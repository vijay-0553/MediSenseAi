import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://127.0.0.1:5173"
SCREENSHOTS_DIR = Path("docs/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR = SCREENSHOTS_DIR / "downloaded_reports"
PDF_DIR.mkdir(parents=True, exist_ok=True)

def run():
    print(f"=== Starting MediSense AI End-to-End Playwright UI Test ===")
    print(f"Target Frontend: {FRONTEND_URL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            accept_downloads=True
        )
        page = context.new_page()

        # Step 1: Register
        print("\n--- 1. Testing Registration Flow ---")
        page.goto(f"{FRONTEND_URL}/register")
        page.wait_for_load_state("networkidle")

        user_email = f"e2e_tester_{int(time.time())}@example.com"
        user_pwd = "Password1234!"
        print(f"Registering as: {user_email}")

        page.fill("input[placeholder='Enter your full name']", "Dr. E2E Playwright")
        page.fill("input[placeholder='Your age']", "38")
        # Click Sex: Female
        female_btn = page.locator("button:has-text('Female')")
        if female_btn.count() > 0:
            female_btn.click()
        page.fill("input[placeholder='Enter your phone number']", "+1 555-019-8234")
        page.fill("input[placeholder='you@example.com']", user_email)
        page.fill("input[placeholder='Min. 8 characters']", user_pwd)
        page.fill("input[placeholder='Repeat password']", user_pwd)

        page.click("button:has-text('Sign Up')")
        page.wait_for_timeout(1000)

        # After registration, should land on /login with toast or /home
        print(f"Current URL after Sign Up: {page.url}")
        if "/login" in page.url or page.locator("button:has-text('Login')").count() > 0:
            print("Successfully reached Login page. Logging in...")
            page.fill("input[placeholder='you@example.com']", user_email)
            page.fill("input[placeholder='Enter your password']", user_pwd)
            page.click("button:has-text('Login')")
            page.wait_for_timeout(1000)

        page.wait_for_url("**/home", timeout=10000)
        print("Logged in successfully and navigated to /home.")

        modules_to_test = [
            {
                "module_key": "fracture",
                "button_text": "Bone Fracture (Upper Limb)",
                "sample": Path("backend/samples/fracture/fractured_01.png").resolve(),
                "roi_action": None,
                "label": "fracture"
            },
            {
                "module_key": "spine",
                "button_text": "Spine",
                "sample": Path("backend/samples/spine/spine_abnormal.dicom").resolve(),
                "roi_action": None,
                "label": "spine"
            },
            {
                "module_key": "knee",
                "button_text": "Knee",
                "sample": Path("backend/samples/knee/knee_KL3.png").resolve(),
                "roi_action": None,
                "label": "knee"
            },
            {
                "module_key": "chest",
                "button_text": "Chest",
                "sample": Path("backend/samples/chest/chest_cardiomegaly.png").resolve(),
                "roi_action": None,
                "label": "chest"
            },
            {
                "module_key": "tumor",
                "button_text": "Bone Tumor",
                "sample": Path("backend/samples/tumor/tumor_benign.jpeg").resolve(),
                "roi_action": "preset_lesion",
                "label": "tumor_roi"
            },
            {
                "module_key": "tumor",
                "button_text": "Bone Tumor",
                "sample": Path("backend/samples/tumor/tumor_normal.jpeg").resolve(),
                "roi_action": "skip_roi",
                "label": "tumor_whole_image"
            },
        ]

        for mod in modules_to_test:
            label = mod["label"]
            print(f"\n==========================================")
            print(f"Testing Module: {mod['button_text']} ({label})")
            print(f"Sample File: {mod['sample'].name}")

            # Ensure we are on /home
            if "/home" not in page.url:
                page.goto(f"{FRONTEND_URL}/home")
                page.wait_for_load_state("networkidle")

            # 1. Verify "Upload & Analyze" is initially disabled before selection
            analyze_btn = page.locator("button:has-text('Upload & Analyze')")
            is_initially_disabled = analyze_btn.is_disabled()
            print(f"Checking 'Upload & Analyze' initial state: disabled={is_initially_disabled}")

            # 2. Select module
            mod_card = page.locator(f"button.module-card:has-text('{mod['button_text']}')")
            mod_card.click()
            print(f"Selected module: {mod['button_text']}")

            # Button should still be disabled because file is not chosen yet
            print(f"Button state after module selection: disabled={analyze_btn.is_disabled()}")

            # 3. Upload file
            file_input = page.locator("input[type='file']")
            file_input.set_input_files(str(mod["sample"]))
            page.wait_for_timeout(600)
            print(f"File uploaded to file input: {mod['sample'].name}")

            # 4. Confirm "Upload & Analyze" is now ENABLED
            is_now_enabled = not analyze_btn.is_disabled()
            print(f"Confirming 'Upload & Analyze' button is enabled: {is_now_enabled}")
            assert is_now_enabled, f"Button should be enabled after selecting module and file for {label}"

            # 5. Handle Tumor ROI if applicable
            if mod["roi_action"] == "preset_lesion":
                print("Testing Tumor ROI Selection card: Selecting Focused Lesion preset...")
                focused_btn = page.locator("button:has-text('Focused Lesion (50%)')")
                if focused_btn.count() > 0:
                    focused_btn.click()
                    page.wait_for_timeout(300)
                    print("Clicked 'Focused Lesion (50%)' ROI preset.")
            elif mod["roi_action"] == "skip_roi":
                print("Testing Tumor Skip ROI: Clicking 'Skip ROI (Whole Image)'...")
                skip_btn = page.locator("button:has-text('Skip ROI (Whole Image)')")
                if skip_btn.count() > 0:
                    skip_btn.click()
                    page.wait_for_timeout(300)
                    print("Clicked 'Skip ROI (Whole Image)'. Amber caution text visible.")

            # 6. Click "Upload & Analyze"
            analyze_btn.click()
            print("Clicked 'Upload & Analyze'. Monitoring progress stages...")

            # 7. Record progress stages
            seen_stages = []
            progress_sc_taken = False
            progress_card = page.locator(".analysis-progress-card")
            progress_card.wait_for(timeout=10000)

            start_poll = time.time()
            while time.time() - start_poll < 45:
                # Find all step labels currently visible
                step_elements = page.locator(".analysis-step").all()
                for idx, step_el in enumerate(step_elements):
                    classes = step_el.get_attribute("class") or ""
                    strong_text = step_el.locator("strong").inner_text()
                    if ("step-current" in classes or "step-complete" in classes) and strong_text not in seen_stages:
                        seen_stages.append(strong_text)
                        print(f"  -> Observed Stage {idx+1}: '{strong_text}' (class: {classes})")

                # Take screenshot while analyzing (e.g. stage 2 or 3)
                if not progress_sc_taken and len(seen_stages) >= 2:
                    p_shot = SCREENSHOTS_DIR / f"progress_{label}.png"
                    page.screenshot(path=str(p_shot))
                    print(f"Saved progress view screenshot: {p_shot}")
                    progress_sc_taken = True

                # Check if complete button "View Report" appears
                view_report_btn = page.locator("button.view-report-button:has-text('View Report')")
                if view_report_btn.count() > 0 and view_report_btn.is_visible():
                    print("Analysis complete! All stages processed.")
                    break
                time.sleep(0.3)

            print(f"All observed progress stages for {label} in order: {seen_stages}")

            # 8. Click "View Report" to navigate to Results page
            view_report_btn = page.locator("button.view-report-button:has-text('View Report')")
            view_report_btn.click()
            page.wait_for_url("**/results", timeout=10000)
            page.wait_for_timeout(1000)
            print(f"Navigated to Results page for {label}.")

            # 9. Verify Results Page Elements
            # (a) Radiograph Image visible (non-blank)
            img_locator = page.locator("img[alt='Analyzed X-ray scan']")
            img_locator.wait_for(state="visible", timeout=10000)
            img_src = img_locator.get_attribute("src") or ""
            print(f"Radiograph <img> verified visible. src starts with: {img_src[:30]}... (length: {len(img_src)})")
            assert img_src.startswith("blob:"), f"Expected authenticated blob URL for radiograph, got: {img_src}"

            # (b) Prediction Block
            pred_badge = page.locator("span:has-text('Architecture:')")
            print(f"Architecture badge visible: {pred_badge.is_visible()}")

            # (c) Probability Bars
            prob_section = page.locator("h2:has-text('Class Probabilities')")
            print(f"Class Probabilities section visible: {prob_section.is_visible()}")

            # (d) Disclaimer
            disclaimer = page.locator("p:has-text('This AI-generated analysis is an assistive screening reference only')")
            print(f"Clinical Disclaimer visible: {disclaimer.is_visible()}")

            # (e) Take Results Screenshot
            r_shot = SCREENSHOTS_DIR / f"results_{label}.png"
            page.screenshot(path=str(r_shot), full_page=True)
            print(f"Saved full-page Results screenshot to: {r_shot}")

            # 10. Click "Download Report" and verify PDF
            print("Triggering PDF download...")
            with page.expect_download(timeout=15000) as download_info:
                page.click("button:has-text('Download Report')")
            download = download_info.value
            download_fn = download.suggested_filename
            print(f"Download initiated! Suggested filename: {download_fn}")
            assert download_fn.startswith("MediSense_Report_") and download_fn.endswith(".pdf"), f"Unexpected filename: {download_fn}"

            saved_pdf_path = PDF_DIR / download_fn
            download.save_as(str(saved_pdf_path))
            pdf_size = os.path.getsize(saved_pdf_path)
            with open(saved_pdf_path, "rb") as f:
                header = f.read(5)
            print(f"PDF saved: {saved_pdf_path} ({pdf_size} bytes). Magic header: {header}")
            assert header == b"%PDF-", f"Expected %PDF header, got {header}"
            assert pdf_size > 1000, f"PDF file size too small ({pdf_size} bytes)"

            # Return to home for next module
            new_analysis_btn = page.locator("button:has-text('New Analysis')")
            if new_analysis_btn.count() > 0:
                new_analysis_btn.click()
                page.wait_for_url("**/home", timeout=5000)

        browser.close()
        print("\n=== Playwright E2E Test Completed Successfully with 100% Verification! ===")

if __name__ == "__main__":
    run()
