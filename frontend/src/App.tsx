import { FormEvent, ReactNode, useEffect, useRef, useState } from "react"
import { api } from "./api/client"
import { PredictionResult, UserProfile } from "./api/types"
import { ResultsPage } from "./ResultsPage"

type Route = "/" | "/register" | "/login" | "/home" | "/results"
type IconName =
  | "activity"
  | "arrow"
  | "bone"
  | "brain"
  | "camera"
  | "check"
  | "eye"
  | "eyeOff"
  | "file"
  | "image"
  | "lock"
  | "logout"
  | "mail"
  | "phone"
  | "scan"
  | "shield"
  | "sparkles"
  | "upload"
  | "user"
  | "x"

const paths: Record<IconName, ReactNode> = {
  activity: <path d="M3 12h4l2.5-7 4 14 2.5-7h5" />,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
  bone: (
    <path d="M7.2 8.5a2.8 2.8 0 1 1-2.7-4.8A2.8 2.8 0 1 1 8.3 7l8.5 8.5a2.8 2.8 0 1 1 2.7 4.8 2.8 2.8 0 1 1-3.8-3.3z" />
  ),
  brain: (
    <>
      <path d="M9.5 4.5A3 3 0 0 0 4 6a3 3 0 0 0 .6 1.8A3.5 3.5 0 0 0 6 14.5V16a3 3 0 0 0 3.5 3" />
      <path d="M14.5 4.5A3 3 0 0 1 20 6a3 3 0 0 1-.6 1.8 3.5 3.5 0 0 1-1.4 6.7V16a3 3 0 0 1-3.5 3M12 4v16M8 9h4m0 6h4" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  camera: (
    <>
      <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
      <circle cx="12" cy="13" r="3" />
    </>
  ),
  eye: (
    <>
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
      <circle cx="12" cy="12" r="2.5" />
    </>
  ),
  eyeOff: (
    <>
      <path d="m3 3 18 18M10.6 6.2c.5-.1.9-.2 1.4-.2 6 0 9.5 6 9.5 6a17 17 0 0 1-2.1 2.8M6.3 6.3C3.9 8 2.5 12 2.5 12s3.5 6 9.5 6c1.6 0 3-.4 4.2-1" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    </>
  ),
  file: (
    <>
      <path d="M7 3h7l4 4v14H7zM14 3v5h5" />
      <path d="M10 13h5m-5 4h5" />
    </>
  ),
  image: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="9" cy="10" r="2" />
      <path d="m4 17 4-4 3 3 3-4 6 6" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="10" width="14" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3m-4 4v3" />
    </>
  ),
  logout: <path d="M10 4H5v16h5m5-4 4-4-4-4m4 4H9" />,
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m4 7 8 6 8-6" />
    </>
  ),
  phone: (
    <>
      <path d="M7 3h10v18H7z" />
      <path d="M11 17h2" />
    </>
  ),
  scan: (
    <>
      <path d="M4 9V5a1 1 0 0 1 1-1h4m6 0h4a1 1 0 0 1 1 1v4m0 6v4a1 1 0 0 1-1 1h-4M9 20H5a1 1 0 0 1-1-1v-4" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3 5 6v5c0 4.7 2.8 8.3 7 10 4.2-1.7 7-5.3 7-10V6z" />
      <path d="m9 12 2 2 4-5" />
    </>
  ),
  sparkles: (
    <>
      <path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2zM6 14l.8 2.2L9 17l-2.2.8L6 20l-.8-2.2L3 17l2.2-.8zM18 14l.6 1.4L20 16l-1.4.6L18 18l-.6-1.4L16 16l1.4-.6z" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16V4m-4 4 4-4 4 4" />
      <path d="M5 14v6h14v-6" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
  x: <path d="m6 6 12 12M18 6 6 18" />,
}

function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      className="icon"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
    >
      {paths[name]}
    </svg>
  )
}

function Logo({ onClick }: { onClick?: () => void }) {
  return (
    <button aria-label="Go to MediSenseAI home" className="logo" onClick={onClick} type="button">
      <span className="logo-mark">
        <Icon name="scan" size={19} />
      </span>
      <span>
        MediSense<span className="text-green">AI</span>
      </span>
    </button>
  )
}

function Button({
  children,
  variant = "primary",
  type = "button",
  onClick,
  disabled,
  className = "",
}: {
  children: ReactNode
  variant?: "primary" | "secondary" | "ghost"
  type?: "button" | "submit"
  onClick?: () => void
  disabled?: boolean
  className?: string
}) {
  return (
    <button
      className={`button button-${variant} ${className}`}
      disabled={disabled}
      onClick={onClick}
      type={type}
    >
      {children}
    </button>
  )
}

function Field({
  label,
  type = "text",
  value,
  placeholder,
  icon,
  error,
  onChange,
  onBlur,
  suffix,
  min,
}: {
  label: string
  type?: string
  value: string
  placeholder: string
  icon: IconName
  error?: string
  onChange: (value: string) => void
  onBlur?: () => void
  suffix?: ReactNode
  min?: string
}) {
  const id = label.toLowerCase().replace(/ /g, "-")
  return (
    <label className={`field ${error ? "field-error" : ""}`} htmlFor={id}>
      <span className="field-label">{label}</span>
      <span className="input-shell">
        <span className="input-icon">
          <Icon name={icon} size={18} />
        </span>
        <input
          aria-describedby={error ? `${id}-error` : undefined}
          aria-invalid={Boolean(error)}
          id={id}
          min={min}
          onBlur={onBlur}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          type={type}
          value={value}
        />
        {suffix}
      </span>
      {error && (
        <span className="error-text" id={`${id}-error`}>
          {error}
        </span>
      )}
    </label>
  )
}

function PasswordField({
  label,
  value,
  placeholder,
  error,
  onChange,
}: {
  label: string
  value: string
  placeholder: string
  error?: string
  onChange: (value: string) => void
}) {
  const [visible, setVisible] = useState(false)
  return (
    <Field
      error={error}
      icon="lock"
      label={label}
      onChange={onChange}
      placeholder={placeholder}
      suffix={
        <button
          aria-label={visible ? "Hide password" : "Show password"}
          className="input-action"
          onClick={() => setVisible(!visible)}
          type="button"
        >
          <Icon name={visible ? "eyeOff" : "eye"} size={19} />
        </button>
      }
      type={visible ? "text" : "password"}
      value={value}
    />
  )
}

function Landing({ navigate }: { navigate: (route: Route) => void }) {
  const steps: { number: string; icon: IconName; title: string; text: string }[] = [
    {
      number: "01",
      icon: "upload",
      title: "Upload X-ray",
      text: "Securely upload a clear image of your X-ray.",
    },
    {
      number: "02",
      icon: "brain",
      title: "AI analysis",
      text: "The right specialist model reviews it in seconds.",
    },
    {
      number: "03",
      icon: "file",
      title: "Get your report",
      text: "Receive clear findings with explainable insights.",
    },
  ]

  return (
    <div className="landing">
      <header className="site-header page-width">
        <Logo onClick={() => navigate("/")} />
        <nav aria-label="Main navigation" className="desktop-nav">
          <a href="#how-it-works">How it works</a>
          <a href="#about">About</a>
          <a href="#models">Models</a>
        </nav>
        <div className="header-actions">
          <Button variant="secondary" onClick={() => navigate("/login")}>
            Login
          </Button>
          <Button onClick={() => navigate("/register")}>Register</Button>
        </div>
      </header>

      <main>
        <section className="hero" id="about">
          <div className="grid-pattern" />
          <div className="hero-glow" />
          <div className="hero-content page-width">
            <div className="eyebrow">
              <Icon name="sparkles" size={15} />
              AI-assisted X-ray analysis
            </div>
            <h1>
              Upload your X-ray.
              <br />
              Get <span className="text-green">instant insights.</span>
            </h1>
            <p className="hero-copy">
              MediSenseAI analyzes chest, spine, knee, upper-limb and bone-tumor X-rays with deep
              learning and gives you an explainable report in seconds.
            </p>
            <div className="hero-actions">
              <Button onClick={() => navigate("/register")}>
                Register
                <Icon name="arrow" size={18} />
              </Button>
              <Button variant="secondary" onClick={() => navigate("/login")}>
                Login
              </Button>
            </div>

            <div className="hero-doctor-showcase" id="models">
              <img
                src="/DOCTOR_LOGO.png"
                alt="MediSense AI Clinical Support Doctor"
                className="hero-doctor-img"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = "/DOCTOR_LOGO.jpg"
                }}
              />
            </div>
          </div>
        </section>

        <section className="steps-section page-width" id="how-it-works">
          <div className="section-heading">
            <span className="section-kicker">Simple by design</span>
            <h2>From X-ray to insight in three steps</h2>
            <p>No complex medical language. Just a secure, guided process.</p>
          </div>
          <div className="steps">
            <div className="step-line" />
            {steps.map((step) => (
              <article className="step-card" key={step.number}>
                <span className="step-number">{step.number}</span>
                <span className="step-icon">
                  <Icon name={step.icon} size={24} />
                </span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="page-width footer-content">
          <Logo onClick={() => navigate("/")} />
          <span>© 2026 MediSenseAI</span>
          <span className="disclaimer">
            AI-assisted decision support. Not a replacement for professional medical diagnosis.
          </span>
        </div>
      </footer>
    </div>
  )
}

type RegisterErrors = Partial<Record<"name" | "age" | "phone" | "email" | "password" | "confirm" | "general", string>>

function Register({
  navigate,
  onSuccess,
}: {
  navigate: (route: Route) => void
  onSuccess: (profile: UserProfile) => void
}) {
  const [form, setForm] = useState({
    name: "",
    age: "",
    sex: "Male",
    phone: "",
    email: "",
    password: "",
    confirm: "",
  })
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<RegisterErrors>({})

  const update = (key: keyof typeof form, value: string) =>
    setForm((current) => ({ ...current, [key]: value }))

  async function submit(event: FormEvent) {
    event.preventDefault()
    const nextErrors: RegisterErrors = {}

    if (!form.name.trim()) {
      nextErrors.name = "Enter your full name"
    }
    const ageNum = parseInt(form.age, 10)
    if (isNaN(ageNum) || ageNum < 1 || ageNum > 130) {
      nextErrors.age = "Enter a valid age (1-130)"
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      nextErrors.email = "Enter a valid email address"
    }
    if (form.password.length < 8) {
      nextErrors.password = "Use at least 8 characters"
    }
    if (form.password !== form.confirm) {
      nextErrors.confirm = "Passwords do not match"
    }

    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setLoading(true)
    try {
      const resp = await api.register({
        name: form.name.trim(),
        age: ageNum,
        sex: form.sex,
        contact: form.phone.trim(),
        email: form.email.trim(),
        password: form.password,
      })
      const normalizedUser = {
        ...resp.user,
        contact: resp.user.contact || form.phone.trim(),
        phone: resp.user.contact || form.phone.trim(),
      }
      sessionStorage.setItem("medisense_token", resp.access_token)
      sessionStorage.setItem("medisense_user", JSON.stringify(normalizedUser))
      onSuccess(normalizedUser)
      navigate("/login")
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Registration failed. Please try again."
      setErrors({ general: msg })
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout navigate={navigate}>
      <form className="auth-card register-card" onSubmit={submit}>
        <div className="auth-heading">
          <span className="auth-icon">
            <Icon name="user" size={24} />
          </span>
          <h1>Create your account</h1>
          <p>Register to start analyzing your X-rays</p>
        </div>

        {errors.general && (
          <div
            style={{
              background: "#fff1f2",
              border: "1px solid #fecdd3",
              color: "#be123c",
              padding: "10px 14px",
              borderRadius: "10px",
              fontSize: "13px",
              marginBottom: "16px",
            }}
          >
            {errors.general}
          </div>
        )}

        <div className="form-grid">
          <Field
            error={errors.name}
            icon="user"
            label="Patient Name"
            onChange={(value) => update("name", value)}
            placeholder="Enter your full name"
            value={form.name}
          />
          <Field
            error={errors.age}
            icon="user"
            label="Age"
            min="1"
            onChange={(value) => update("age", value)}
            placeholder="Your age"
            type="number"
            value={form.age}
          />
        </div>
        <fieldset className="field sex-field">
          <legend className="field-label">Sex</legend>
          <div className="segment">
            {["Male", "Female", "Other"].map((item) => (
              <button
                aria-pressed={form.sex === item}
                className={form.sex === item ? "segment-active" : ""}
                key={item}
                onClick={() => update("sex", item)}
                type="button"
              >
                {item}
              </button>
            ))}
          </div>
        </fieldset>
        <Field
          error={errors.phone}
          icon="phone"
          label="Contact Number"
          onChange={(value) => update("phone", value)}
          placeholder="Enter your phone number"
          type="tel"
          value={form.phone}
        />
        <Field
          error={errors.email}
          icon="mail"
          label="Email"
          onChange={(value) => {
            update("email", value)
            if (errors.email) setErrors({ ...errors, email: undefined })
          }}
          placeholder="you@example.com"
          type="email"
          value={form.email}
        />
        <div className="form-grid">
          <PasswordField
            error={errors.password}
            label="Password"
            onChange={(value) => update("password", value)}
            placeholder="Min. 8 characters"
            value={form.password}
          />
          <PasswordField
            error={errors.confirm}
            label="Confirm Password"
            onChange={(value) => {
              update("confirm", value)
              if (errors.confirm) setErrors({ ...errors, confirm: undefined })
            }}
            placeholder="Repeat password"
            value={form.confirm}
          />
        </div>
        <Button className="full-button" disabled={loading} type="submit">
          {loading ? "Creating account..." : "Sign Up"}
          <Icon name="arrow" size={18} />
        </Button>
        <p className="auth-switch">
          Already have an account?{" "}
          <button onClick={() => navigate("/login")} type="button">
            Login
          </button>
        </p>
      </form>
    </AuthLayout>
  )
}

function Login({
  navigate,
  showToast,
  onLoginSuccess,
}: {
  navigate: (route: Route) => void
  showToast: boolean
  onLoginSuccess: (user: UserProfile) => void
}) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const resp = await api.login({ email, password })
      const normalizedUser = {
        ...resp.user,
        contact: resp.user.contact || (resp.user as any).phone || "",
        phone: resp.user.contact || (resp.user as any).phone || "",
      }
      sessionStorage.setItem("medisense_token", resp.access_token)
      sessionStorage.setItem("medisense_user", JSON.stringify(normalizedUser))
      onLoginSuccess(normalizedUser)
      navigate("/home")
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Invalid email or password."
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout navigate={navigate}>
      {showToast && (
        <div className="toast" role="status">
          <span className="toast-icon">
            <Icon name="check" size={16} />
          </span>
          <span>
            <strong>Account created successfully</strong>
            <small>You can now log in to MediSenseAI.</small>
          </span>
        </div>
      )}
      <form className="auth-card login-card" onSubmit={handleSubmit}>
        <div className="auth-heading">
          <span className="auth-icon">
            <Icon name="lock" size={23} />
          </span>
          <h1>Welcome back</h1>
          <p>Log in to continue to your health dashboard</p>
        </div>

        {error && (
          <div
            style={{
              background: "#fff1f2",
              border: "1px solid #fecdd3",
              color: "#be123c",
              padding: "10px 14px",
              borderRadius: "10px",
              fontSize: "13px",
              marginBottom: "16px",
            }}
          >
            {error}
          </div>
        )}

        <Field
          icon="mail"
          label="Email"
          onChange={setEmail}
          placeholder="you@example.com"
          type="email"
          value={email}
        />
        <PasswordField
          label="Password"
          onChange={setPassword}
          placeholder="Enter your password"
          value={password}
        />
        <div className="forgot-row">
          <button type="button">Forgot password?</button>
        </div>
        <Button className="full-button" disabled={loading} type="submit">
          {loading ? "Logging in..." : "Login"}
          <Icon name="arrow" size={18} />
        </Button>
        <p className="auth-switch">
          New here?{" "}
          <button onClick={() => navigate("/register")} type="button">
            Register
          </button>
        </p>
      </form>
      <div className="trust-note">
        <Icon name="shield" size={16} />
        Your data is private and securely protected
      </div>
    </AuthLayout>
  )
}

function AuthLayout({ navigate, children }: { navigate: (route: Route) => void; children: ReactNode }) {
  return (
    <main className="auth-page">
      <div className="grid-pattern" />
      <div className="auth-glow auth-glow-one" />
      <div className="auth-glow auth-glow-two" />
      <div className="auth-shell">
        <Logo onClick={() => navigate("/")} />
        {children}
      </div>
    </main>
  )
}

const modules: { name: string; shortName: string; icon: IconName; key: string }[] = [
  { name: "Bone Fracture (Upper Limb)", shortName: "Bone Fracture", icon: "bone", key: "fracture" },
  { name: "Bone Tumor", shortName: "Bone Tumor", icon: "sparkles", key: "tumor" },
  { name: "Spine", shortName: "Spine", icon: "activity", key: "spine" },
  { name: "Knee", shortName: "Knee", icon: "scan", key: "knee" },
  { name: "Chest", shortName: "Chest", icon: "shield", key: "chest" },
]

function PatientAvatar({ profile, className = "" }: { profile: UserProfile; className?: string }) {
  const [avatarError, setAvatarError] = useState(false)
  const token = sessionStorage.getItem("medisense_token")

  if (profile.avatar_url && !avatarError && token) {
    const fullAvatarUrl = profile.avatar_url.startsWith("http")
      ? profile.avatar_url
      : `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${profile.avatar_url}`

    return (
      <img
        alt={profile.name}
        className={`patient-avatar ${className}`}
        onError={() => setAvatarError(true)}
        src={fullAvatarUrl}
      />
    )
  }

  const initials = profile.name
    ? profile.name
        .split(" ")
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "PT"

  return <span className={`patient-avatar avatar-initials ${className}`}>{initials}</span>
}

function AuthenticatedHeader({
  navigate,
  profile,
  onProfile,
}: {
  navigate: (route: Route) => void
  profile: UserProfile
  onProfile: () => void
}) {
  return (
    <header className="app-header">
      <div className="page-width app-header-inner">
        <Logo onClick={() => navigate("/home")} />
        <nav aria-label="Authenticated navigation" className="app-nav">
          <button className="app-nav-active" onClick={() => navigate("/home")} type="button">
            Home
          </button>
          <button onClick={() => navigate("/")} type="button">
            About Us
          </button>
          <button onClick={() => navigate("/")} type="button">
            How It Works
          </button>
        </nav>
        <button aria-label="Open profile" className="avatar-button" onClick={onProfile} type="button">
          <PatientAvatar profile={profile} />
          <span className="avatar-status" />
        </button>
      </div>
    </header>
  )
}

function MedicalFooter() {
  return (
    <footer className="app-footer">
      <div className="page-width app-footer-inner">
        <span className="footer-shield">
          <Icon name="shield" size={16} />
        </span>
        <span>
          AI-assisted decision support. Not a replacement for professional medical diagnosis.
        </span>
        <span className="app-footer-copy">© 2026 MediSenseAI</span>
      </div>
    </footer>
  )
}

function ProfileDrawer({
  profile,
  onUpdate,
  onClose,
  onLogout,
}: {
  profile: UserProfile
  onUpdate: (profile: UserProfile) => void
  onClose: () => void
  onLogout: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(profile)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [uploadingAvatar, setUploadingAvatar] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const photoInput = useRef<HTMLInputElement>(null)

  function updateDraft(key: keyof UserProfile, value: string) {
    setDraft((current) => ({
      ...current,
      [key]: value,
      ...(key === "contact" ? { phone: value } : {}),
      ...(key === "phone" ? { contact: value } : {}),
    }))
  }

  async function handleSave() {
    setSaveLoading(true)
    setErrorMsg(null)
    try {
      const updated = await api.updateMe({
        name: draft.name,
        age: draft.age,
        sex: draft.sex,
        contact: draft.contact || draft.phone,
        email: draft.email,
      })
      const normalized = {
        ...updated,
        contact: updated.contact || (updated as any).phone || "",
        phone: updated.contact || (updated as any).phone || "",
      }
      onUpdate(normalized)
      sessionStorage.setItem("medisense_user", JSON.stringify(normalized))
      setEditing(false)
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Failed to update profile.")
    } finally {
      setSaveLoading(false)
    }
  }

  async function handleAvatarUpload(file: File) {
    setUploadingAvatar(true)
    setErrorMsg(null)
    try {
      const updated = await api.uploadAvatar(file)
      const normalized = {
        ...updated,
        contact: updated.contact || (updated as any).phone || "",
        phone: updated.contact || (updated as any).phone || "",
      }
      onUpdate(normalized)
      sessionStorage.setItem("medisense_user", JSON.stringify(normalized))
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Failed to upload avatar.")
    } finally {
      setUploadingAvatar(false)
    }
  }

  const details: { key: keyof UserProfile; label: string; icon: IconName }[] = [
    { key: "name", label: "Patient Name", icon: "user" },
    { key: "age", label: "Age", icon: "activity" },
    { key: "sex", label: "Sex", icon: "user" },
    { key: "contact", label: "Contact", icon: "phone" },
    { key: "email", label: "Email", icon: "mail" },
  ]

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside aria-label="Patient profile" className="profile-drawer">
        <div className="drawer-header">
          <div>
            <span className="drawer-kicker">Your account</span>
            <h2>Profile</h2>
          </div>
          <button aria-label="Close profile" className="close-button" onClick={onClose} type="button">
            <Icon name="x" />
          </button>
        </div>

        {errorMsg && (
          <div
            style={{
              background: "#fff1f2",
              border: "1px solid #fecdd3",
              color: "#be123c",
              padding: "10px 14px",
              borderRadius: "10px",
              fontSize: "12px",
              marginBottom: "12px",
            }}
          >
            {errorMsg}
          </div>
        )}

        <div className="profile-identity">
          <div className="large-avatar-wrap">
            <PatientAvatar className="large-avatar" profile={profile} />
            <button
              aria-label="Edit profile photo"
              className="camera-button"
              disabled={uploadingAvatar}
              onClick={() => photoInput.current?.click()}
              type="button"
            >
              <Icon name="camera" size={16} />
            </button>
            <input
              accept="image/*"
              className="visually-hidden"
              onChange={(event) => {
                const photo = event.target.files?.[0]
                if (photo) handleAvatarUpload(photo)
              }}
              ref={photoInput}
              type="file"
            />
          </div>
          <strong>{profile.name}</strong>
          <button
            className="edit-photo-link"
            disabled={uploadingAvatar}
            onClick={() => photoInput.current?.click()}
            type="button"
          >
            {uploadingAvatar ? "Uploading photo..." : "Edit photo"}
          </button>
        </div>

        <div className="profile-details">
          {editing
            ? details.map((detail) => {
                const val = detail.key === "contact"
                  ? (draft.contact || draft.phone || "")
                  : (draft[detail.key] || "")
                return (
                  <Field
                    icon={detail.icon}
                    key={detail.key}
                    label={detail.label}
                    onChange={(value) => updateDraft(detail.key, value)}
                    placeholder={detail.label}
                    type={detail.key === "email" ? "email" : "text"}
                    value={String(val)}
                  />
                )
              })
            : details.map((detail) => {
                const val = detail.key === "contact"
                  ? (profile.contact || profile.phone)
                  : profile[detail.key]
                return (
                  <div className="profile-detail" key={detail.key}>
                    <span className="profile-detail-icon">
                      <Icon name={detail.icon} size={18} />
                    </span>
                    <span>
                      <small>{detail.label}</small>
                      <strong>{val || "Not provided"}</strong>
                    </span>
                  </div>
                )
              })}
        </div>

        {editing ? (
          <div className="drawer-action-row">
            <Button
              variant="secondary"
              onClick={() => {
                setDraft(profile)
                setEditing(false)
              }}
            >
              Cancel
            </Button>
            <Button disabled={saveLoading} onClick={handleSave}>
              {saveLoading ? "Saving..." : "Save changes"}
            </Button>
          </div>
        ) : (
          <Button className="drawer-button" variant="secondary" onClick={() => setEditing(true)}>
            Edit Details
          </Button>
        )}
        <Button className="drawer-button" variant="secondary" onClick={() => setPasswordOpen(true)}>
          <Icon name="lock" size={17} />
          Change Password
        </Button>
        <button className="logout-button" onClick={onLogout} type="button">
          <Icon name="logout" size={18} />
          Logout
        </button>
      </aside>
      {passwordOpen && <PasswordModal onClose={() => setPasswordOpen(false)} />}
    </>
  )
}

function PasswordModal({ onClose }: { onClose: () => void }) {
  const [current, setCurrent] = useState("")
  const [next, setNext] = useState("")
  const [confirm, setConfirm] = useState("")
  const [updated, setUpdated] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handlePasswordSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await api.updatePassword({
        current_password: current,
        new_password: next,
      })
      setUpdated(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to update password.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div aria-modal="true" className="modal-layer" role="dialog">
      <div className="password-modal">
        <div className="modal-heading">
          <span className="auth-icon">
            <Icon name="lock" size={22} />
          </span>
          <div>
            <h2>Change password</h2>
            <p>Choose a strong password you haven’t used before.</p>
          </div>
          <button aria-label="Close modal" className="close-button" onClick={onClose} type="button">
            <Icon name="x" />
          </button>
        </div>

        {error && (
          <div
            style={{
              background: "#fff1f2",
              border: "1px solid #fecdd3",
              color: "#be123c",
              padding: "10px 14px",
              borderRadius: "10px",
              fontSize: "13px",
              marginBottom: "16px",
            }}
          >
            {error}
          </div>
        )}

        {updated ? (
          <div className="password-success">
            <span className="success-orb">
              <Icon name="check" size={28} />
            </span>
            <h3>Password updated</h3>
            <p>Your new password is ready to use.</p>
            <Button onClick={onClose}>Done</Button>
          </div>
        ) : (
          <form onSubmit={handlePasswordSubmit}>
            <PasswordField
              label="Current Password"
              onChange={setCurrent}
              placeholder="Enter current password"
              value={current}
            />
            <PasswordField
              label="New Password"
              onChange={setNext}
              placeholder="Min. 8 characters"
              value={next}
            />
            <PasswordField
              error={confirm && confirm !== next ? "Passwords do not match" : undefined}
              label="Confirm New Password"
              onChange={setConfirm}
              placeholder="Repeat new password"
              value={confirm}
            />
            <Button
              className="full-button"
              disabled={loading || !current || next.length < 8 || next !== confirm}
              type="submit"
            >
              {loading ? "Updating..." : "Update Password"}
            </Button>
          </form>
        )}
      </div>
    </div>
  )
}

function AnalysisProgress({
  file,
  fileObj,
  module,
  roiBox,
  onViewReport,
  onRetry,
  onChooseAnother,
}: {
  file: { name: string; url: string }
  fileObj: File
  module: typeof modules[number]
  roiBox?: number[] | null
  onViewReport: (result: PredictionResult) => void
  onRetry: () => void
  onChooseAnother: () => void
}) {
  const labels = [
    "X-ray uploaded",
    "X-ray fetched",
    "Model analyzing",
    "Report generation",
    "Report generated successfully",
  ]

  // Step 1: Upload (0-20%)
  // Step 2: Fetched (20-40%)
  // Step 3: Analyzing (40-65%)
  // Step 4: Report generation (65-85%)
  // Step 5: Complete (100%)
  const [currentStep, setCurrentStep] = useState<number>(0)
  const [progressPercent, setProgressPercent] = useState<number>(5)
  const [finalResult, setFinalResult] = useState<PredictionResult | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const isDicom = file.name.toLowerCase().endsWith(".dcm") || file.name.toLowerCase().endsWith(".dicom")

  useEffect(() => {
    let isCancelled = false
    let pollInterval: any = null

    async function runJobFlow() {
      try {
        setErrorMessage(null)
        setCurrentStep(0)
        setProgressPercent(10)

        // 1. Upload File with Progress (Step 1: X-ray uploaded)
        const jobInit = await api.createJob(module.key, fileObj, (progressEvent) => {
          if (progressEvent.total) {
            const uploadPct = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            // Upload maps to 10% .. 25%
            const scaled = 10 + Math.round((uploadPct * 15) / 100)
            if (!isCancelled) setProgressPercent(scaled)
          }
        }, roiBox)

        if (isCancelled) return

        // Step 2: Fetched (Server returned 202 with job_id)
        setCurrentStep(1)
        setProgressPercent(35)
        const jobId = jobInit.job_id

        // Ensure Step 2 is observable
        await new Promise((resolve) => setTimeout(resolve, 400))
        if (isCancelled) return

        // 2. Poll GET /api/jobs/{id} every 800ms with transient error tolerance
        let consecutiveFailures = 0
        const MAX_CONSECUTIVE_FAILURES = 35

        pollInterval = setInterval(async () => {
          try {
            const jobData = await api.getJobStatus(jobId)
            if (isCancelled) return
            consecutiveFailures = 0

            if (jobData.status === "analyzing") {
              // Step 3: Model analyzing
              setCurrentStep(2)
              setProgressPercent(60)
            } else if (jobData.status === "generating_report") {
              // Step 4: Report generation
              setCurrentStep(3)
              setProgressPercent(82)
            } else if (jobData.status === "done") {
              // Step 5: Complete
              clearInterval(pollInterval)
              setCurrentStep(4)
              setProgressPercent(100)
              if (jobData.result) {
                setFinalResult(jobData.result)
                sessionStorage.setItem("medisense_latest_result", JSON.stringify(jobData.result))
              }
            } else if (jobData.status === "failed") {
              clearInterval(pollInterval)
              setErrorMessage(jobData.error || "Model analysis failed. Please verify the image and try again.")
            }
          } catch (pollErr: any) {
            console.warn("Polling retryable error:", pollErr)
            consecutiveFailures++
            if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
              clearInterval(pollInterval)
              setErrorMessage("Failed to check analysis progress. The server may be unreachable.")
            }
          }
        }, 800)

      } catch (err: any) {
        if (isCancelled) return
        const detail = err.response?.data?.detail || err.message || "Failed to upload X-ray."
        setErrorMessage(detail)
      }
    }

    runJobFlow()

    return () => {
      isCancelled = true
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [fileObj, module.key])

  return (
    <section
      className={`analysis-progress-card ${
        progressPercent === 100 ? "analysis-complete" : ""
      }`}
    >
      <div className="progress-topline">
        <div>
          <span className="card-step">AI analysis</span>
          <h2>
            {errorMessage
              ? "Analysis stopped"
              : progressPercent === 100
              ? "Your report is ready"
              : "Analyzing your X-ray"}
          </h2>
          <p>
            {errorMessage
              ? "An issue occurred during evaluation. You can retry or choose another file."
              : progressPercent === 100
              ? "Your explainable AI report was generated successfully."
              : "Please keep this window open while our model processes your image."}
          </p>
        </div>
        <strong
          className="progress-percent"
          style={{ color: errorMessage ? "#d13f4b" : undefined }}
        >
          {errorMessage ? "Error" : `${progressPercent}%`}
        </strong>
      </div>

      <div className="analysis-file-row">
        {isDicom ? (
          <div
            style={{
              width: "56px",
              height: "56px",
              background: "#e8f8ee",
              borderRadius: "10px",
              display: "grid",
              placeItems: "center",
              color: "#00c853",
              fontWeight: 800,
              fontSize: "11px",
              letterSpacing: "0.05em",
            }}
          >
            DICOM
          </div>
        ) : (
          <img alt="Uploaded X-ray preview" src={file.url} />
        )}
        <span>
          <small>Selected scan</small>
          <strong>{file.name}</strong>
          <em>{module.shortName} Module</em>
        </span>
        {progressPercent === 100 && (
          <span className="success-badge">
            <Icon name="check" size={16} />
            Complete
          </span>
        )}
      </div>

      {errorMessage ? (
        <div
          style={{
            background: "#fff1f2",
            border: "1.5px solid #fecdd3",
            borderRadius: "14px",
            padding: "16px 20px",
            margin: "20px 0",
            color: "#9f1239",
            fontSize: "13.5px",
            lineHeight: 1.5,
          }}
        >
          <strong>Error: </strong> {errorMessage}
          <div style={{ display: "flex", gap: "12px", marginTop: "14px" }}>
            <Button onClick={onRetry}>Retry Analysis</Button>
            <Button variant="secondary" onClick={onChooseAnother}>
              Choose another file
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div
            className="progress-track"
            aria-label={`Analysis ${progressPercent}% complete`}
          >
            <span style={{ width: `${progressPercent}%` }} />
          </div>

          <div className="analysis-stepper">
            {labels.map((label, index) => {
              const isPast = index < currentStep
              const isCurrent = index === currentStep
              return (
                <div
                  className={`analysis-step ${isPast ? "step-complete" : ""} ${
                    isCurrent ? "step-current" : ""
                  }`}
                  key={label}
                >
                  <span className="analysis-step-marker">
                    {isPast || progressPercent === 100 ? (
                      <Icon name="check" size={15} />
                    ) : (
                      <span className="step-dot" />
                    )}
                  </span>
                  <span>
                    <small>0{index + 1}</small>
                    <strong>{label}</strong>
                  </span>
                </div>
              )
            })}
          </div>

          {progressPercent === 100 && finalResult && (
            <Button
              className="view-report-button"
              onClick={() => onViewReport(finalResult)}
            >
              View Report
              <Icon name="arrow" size={18} />
            </Button>
          )}
        </>
      )}
    </section>
  )
}

function Home({
  navigate,
  profile,
  onProfileUpdate,
  onAnalysisDone,
}: {
  navigate: (route: Route) => void
  profile: UserProfile
  onProfileUpdate: (profile: UserProfile) => void
  onAnalysisDone: (result: PredictionResult) => void
}) {
  const [profileOpen, setProfileOpen] = useState(false)
  const [selected, setSelected] = useState<typeof modules[number] | null>(null)
  const [file, setFile] = useState<{ name: string; url: string } | null>(null)
  const [fileObj, setFileObj] = useState<File | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [roiBox, setRoiBox] = useState<[number, number, number, number]>([0.2, 0.2, 0.8, 0.8])
  const [skipRoi, setSkipRoi] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  function selectFile(nextFile?: File) {
    if (!nextFile) return
    setFileObj(nextFile)
    const url = URL.createObjectURL(nextFile)
    setFile({ name: nextFile.name, url })
    setSkipRoi(false)
  }

  const isDicom =
    file?.name.toLowerCase().endsWith(".dcm") ||
    file?.name.toLowerCase().endsWith(".dicom")
  const isTumor = selected?.key === "tumor"

  return (
    <div className="app-shell">
      <AuthenticatedHeader
        navigate={navigate}
        onProfile={() => setProfileOpen(true)}
        profile={profile}
      />
      <main className="home-main">
        <section className="home-intro page-width">
          <div>
            <span className="eyebrow">
              <Icon name="sparkles" size={15} />
              AI-powered imaging insights
            </span>
            <p className="greeting">Hello, {profile.name ? profile.name.split(" ")[0] : "Patient"}</p>
            <h1>
              Upload your X-ray for{" "}
              <span className="text-green">instant AI analysis</span>
            </h1>
            <p className="home-intro-copy">
              Select the scan type, securely upload your image, and receive
              clear, explainable insights in seconds.
            </p>
          </div>
          <div className="security-pill">
            <span>
              <Icon name="shield" size={20} />
            </span>
            <div>
              <strong>Secure &amp; private</strong>
              <small>Your files are encrypted</small>
            </div>
          </div>
        </section>

        <section className="page-width workflow-wrap">
          {analyzing && file && fileObj && selected ? (
            <AnalysisProgress
              file={file}
              fileObj={fileObj}
              module={selected}
              roiBox={isTumor && !skipRoi ? roiBox : null}
              onChooseAnother={() => {
                setAnalyzing(false)
                setFile(null)
                setFileObj(null)
              }}
              onRetry={() => {
                setAnalyzing(false)
                setTimeout(() => setAnalyzing(true), 50)
              }}
              onViewReport={(result) => {
                onAnalysisDone(result)
                navigate("/results")
              }}
            />
          ) : (
            <div className="workflow-card">
              <div className="workflow-section">
                <div className="workflow-heading">
                  <span className="workflow-number">1</span>
                  <div>
                    <span className="card-step">Step 1</span>
                    <h2>Select X-ray type</h2>
                    <p>Choose the module that best matches your scan.</p>
                  </div>
                </div>
                <div className="module-grid">
                  {modules.map((m) => (
                    <button
                      aria-pressed={selected?.name === m.name}
                      className={`module-card ${
                        selected?.name === m.name ? "module-selected" : ""
                      }`}
                      key={m.name}
                      onClick={() => setSelected(m)}
                      type="button"
                    >
                      <span className="module-icon">
                        <Icon name={m.icon} size={23} />
                      </span>
                      <strong>{m.name}</strong>
                      {selected?.name === m.name && (
                        <span className="module-check">
                          <Icon name="check" size={13} />
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              <div className="workflow-divider" />

              <div className="workflow-section">
                <div className="workflow-heading">
                  <span className="workflow-number">2</span>
                  <div>
                    <span className="card-step">Step 2</span>
                    <h2>Upload your X-ray</h2>
                    <p>Use the original, highest-quality scan available.</p>
                  </div>
                </div>
                <button
                  className={`upload-dropzone ${file ? "upload-has-file" : ""}`}
                  onClick={() => fileInput.current?.click()}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => {
                    event.preventDefault()
                    selectFile(event.dataTransfer.files[0])
                  }}
                  type="button"
                >
                  <input
                    accept=".jpg,.jpeg,.png,.dcm,.dicom,image/jpeg,image/png"
                    className="visually-hidden"
                    onChange={(event) => selectFile(event.target.files?.[0])}
                    ref={fileInput}
                    type="file"
                  />
                  {file ? (
                    <div className="file-preview">
                      {isDicom ? (
                        <div
                          style={{
                            width: "56px",
                            height: "56px",
                            background: "#e8f8ee",
                            borderRadius: "10px",
                            display: "grid",
                            placeItems: "center",
                            color: "#00c853",
                            fontWeight: 800,
                            fontSize: "11px",
                            letterSpacing: "0.05em",
                          }}
                        >
                          DICOM
                        </div>
                      ) : (
                        <img alt="Selected X-ray preview" src={file.url} />
                      )}
                      <div>
                        <span className="file-ready">
                          <Icon name="check" size={13} />
                          Ready to analyze
                        </span>
                        <strong>{file.name}</strong>
                        <small>Click to replace this file</small>
                      </div>
                      <span
                        aria-label="Remove file"
                        className="remove-file"
                        onClick={(event) => {
                          event.stopPropagation()
                          setFile(null)
                          setFileObj(null)
                        }}
                        role="button"
                        tabIndex={0}
                      >
                        <Icon name="x" size={17} />
                      </span>
                    </div>
                  ) : (
                    <>
                      <span className="upload-icon">
                        <Icon name="upload" size={28} />
                      </span>
                      <strong>Drop your X-ray here</strong>
                      <p>
                        or <span>browse files</span> from your computer
                      </p>
                      <div className="format-pills">
                        <span>JPG</span>
                        <span>PNG</span>
                        <span>DICOM</span>
                      </div>
                      <small>Max 25 MB. Processed securely.</small>
                    </>
                  )}
                </button>
              </div>

              {/* Tumor Optional ROI Selection Card */}
              {isTumor && file && !isDicom && (
                <div
                  style={{
                    background: "#f0fdf4",
                    border: "1.5px solid #86efac",
                    borderRadius: "16px",
                    padding: "20px",
                    margin: "12px 24px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", marginBottom: "12px" }}>
                    <div>
                      <strong style={{ color: "#166534", fontSize: "14px", display: "block" }}>
                        Targeted Region of Interest (ROI) Selection (Optional)
                      </strong>
                      <p style={{ margin: "3px 0 0", color: "#15803d", fontSize: "12.5px", lineHeight: 1.4 }}>
                        The bone tumor model was trained on cropped tumor lesions. Select the suspected region, or skip to analyze the whole image.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSkipRoi(!skipRoi)}
                      style={{
                        background: skipRoi ? "#dcfce7" : "#ffffff",
                        border: "1.5px solid #86efac",
                        borderRadius: "8px",
                        padding: "6px 14px",
                        fontSize: "12px",
                        fontWeight: 700,
                        cursor: "pointer",
                        color: skipRoi ? "#166534" : "#15803d",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {skipRoi ? "✓ Enable ROI Crop" : "Skip ROI (Whole Image)"}
                    </button>
                  </div>

                  {!skipRoi ? (
                    <div>
                      <div
                        style={{
                          position: "relative",
                          width: "100%",
                          maxWidth: "380px",
                          height: "220px",
                          background: "#0d1611",
                          borderRadius: "12px",
                          overflow: "hidden",
                          margin: "0 auto 12px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <img
                          src={file.url}
                          alt="Tumor preview for ROI"
                          style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain", opacity: 0.85 }}
                        />
                        {/* Selected ROI Boundary */}
                        <div
                          style={{
                            position: "absolute",
                            left: `${roiBox[0] * 100}%`,
                            top: `${roiBox[1] * 100}%`,
                            width: `${(roiBox[2] - roiBox[0]) * 100}%`,
                            height: `${(roiBox[3] - roiBox[1]) * 100}%`,
                            border: "2px dashed #00c853",
                            background: "rgba(0, 200, 83, 0.18)",
                            borderRadius: "4px",
                            boxShadow: "0 0 10px rgba(0, 200, 83, 0.4)",
                            pointerEvents: "none",
                          }}
                        >
                          <span
                            style={{
                              position: "absolute",
                              top: "4px",
                              left: "6px",
                              background: "#00c853",
                              color: "#ffffff",
                              fontSize: "10px",
                              fontWeight: 700,
                              padding: "1px 5px",
                              borderRadius: "3px",
                            }}
                          >
                            Lesion ROI
                          </span>
                        </div>
                      </div>

                      {/* ROI Preset Adjusters */}
                      <div style={{ display: "flex", justifyContent: "center", gap: "8px", flexWrap: "wrap" }}>
                        <button
                          type="button"
                          onClick={() => setRoiBox([0.2, 0.2, 0.8, 0.8])}
                          style={{
                            background: "#ffffff",
                            border: "1px solid #bbf7d0",
                            borderRadius: "6px",
                            padding: "4px 10px",
                            fontSize: "12px",
                            cursor: "pointer",
                            color: "#166534",
                          }}
                        >
                          Center 60%
                        </button>
                        <button
                          type="button"
                          onClick={() => setRoiBox([0.15, 0.05, 0.85, 0.55])}
                          style={{
                            background: "#ffffff",
                            border: "1px solid #bbf7d0",
                            borderRadius: "6px",
                            padding: "4px 10px",
                            fontSize: "12px",
                            cursor: "pointer",
                            color: "#166534",
                          }}
                        >
                          Upper Region
                        </button>
                        <button
                          type="button"
                          onClick={() => setRoiBox([0.15, 0.45, 0.85, 0.95])}
                          style={{
                            background: "#ffffff",
                            border: "1px solid #bbf7d0",
                            borderRadius: "6px",
                            padding: "4px 10px",
                            fontSize: "12px",
                            cursor: "pointer",
                            color: "#166534",
                          }}
                        >
                          Lower Region
                        </button>
                        <button
                          type="button"
                          onClick={() => setRoiBox([0.25, 0.25, 0.75, 0.75])}
                          style={{
                            background: "#ffffff",
                            border: "1px solid #bbf7d0",
                            borderRadius: "6px",
                            padding: "4px 10px",
                            fontSize: "12px",
                            cursor: "pointer",
                            color: "#166534",
                          }}
                        >
                          Focused Lesion (50%)
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ fontSize: "12px", color: "#d97706", marginTop: "4px" }}>
                      ⚠️ ROI selection skipped. Whole-image analysis will be evaluated (outside training setup; not a screening result).
                    </div>
                  )}
                </div>
              )}

              <div className="analyze-row">
                <span>
                  <Icon name="shield" size={16} />
                  Images are deleted after processing
                </span>
                <Button
                  disabled={!selected || !file}
                  onClick={() => setAnalyzing(true)}
                >
                  <Icon name="sparkles" size={18} />
                  Upload &amp; Analyze
                </Button>
              </div>
            </div>
          )}
        </section>

        <section className="page-width supported-section">
          <div className="supported-heading">
            <div>
              <span className="section-kicker">Specialist models</span>
              <h2>Supported modules</h2>
            </div>
            <p>
              Five purpose-built AI models, each trained for a specific X-ray
              type.
            </p>
          </div>
          <div className="supported-grid">
            {modules.map((m) => (
              <button
                className="supported-card"
                key={m.name}
                onClick={() => {
                  setSelected(m)
                  window.scrollTo({ top: 220, behavior: "smooth" })
                }}
                type="button"
              >
                <span>
                  <Icon name={m.icon} size={19} />
                </span>
                <strong>{m.shortName}</strong>
              </button>
            ))}
          </div>
        </section>
      </main>
      <MedicalFooter />
      {profileOpen && (
        <ProfileDrawer
          onClose={() => setProfileOpen(false)}
          onLogout={() => {
            sessionStorage.removeItem("medisense_token")
            sessionStorage.removeItem("medisense_user")
            navigate("/login")
          }}
          onUpdate={onProfileUpdate}
          profile={profile}
        />
      )}
    </div>
  )
}

function getRoute(): Route {
  return (
    ["/", "/register", "/login", "/home", "/results"].includes(
      window.location.pathname,
    )
      ? window.location.pathname
      : "/"
  ) as Route
}

export default function App() {
  const [route, setRoute] = useState<Route>(getRoute)
  const [showToast, setShowToast] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  // Load user profile from sessionStorage if logged in
  const [profile, setProfile] = useState<UserProfile>(() => {
    const saved = sessionStorage.getItem("medisense_user")
    if (saved) {
      try {
        const u = JSON.parse(saved)
        if (u.contact && !u.phone) u.phone = u.contact
        if (u.phone && !u.contact) u.contact = u.phone
        return u
      } catch {
        // ignore
      }
    }
    return {
      name: "",
      age: "30",
      sex: "Not specified",
      phone: "",
      contact: "",
      email: "",
    }
  })

  // Load last prediction result if available
  const [latestResult, setLatestResult] = useState<PredictionResult | null>(() => {
    const saved = sessionStorage.getItem("medisense_latest_result")
    if (saved) {
      try {
        return JSON.parse(saved)
      } catch {
        // ignore
      }
    }
    return null
  })

  useEffect(() => {
    const onPopState = () => setRoute(getRoute())
    window.addEventListener("popstate", onPopState)

    // Listen for unauthorized events to redirect to login
    const onUnauthorized = () => {
      navigate("/login")
    }
    window.addEventListener("medisense_unauthorized", onUnauthorized)

    // Check token on mount
    const token = sessionStorage.getItem("medisense_token")
    if (token) {
      api.getMe().then((me) => {
        const normalized = {
          ...me,
          phone: me.contact || (me as any).phone || "",
          contact: me.contact || (me as any).phone || "",
        }
        setProfile(normalized)
        sessionStorage.setItem("medisense_user", JSON.stringify(normalized))
      }).catch(() => {
        // token expired or invalid
      })
    }

    return () => {
      window.removeEventListener("popstate", onPopState)
      window.removeEventListener("medisense_unauthorized", onUnauthorized)
    }
  }, [])

  function navigate(nextRoute: Route) {
    window.history.pushState({}, "", nextRoute)
    setRoute(nextRoute)
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  // Route protection
  const token = sessionStorage.getItem("medisense_token")
  if ((route === "/home" || route === "/results") && !token) {
    return <Login navigate={navigate} showToast={false} onLoginSuccess={setProfile} />
  }

  if (route === "/register") {
    return (
      <Register
        navigate={navigate}
        onSuccess={(newProfile) => {
          setProfile(newProfile)
          setShowToast(true)
          window.setTimeout(() => setShowToast(false), 5000)
        }}
      />
    )
  }

  if (route === "/login") {
    return <Login navigate={navigate} showToast={showToast} onLoginSuccess={setProfile} />
  }

  if (route === "/home") {
    return (
      <Home
        navigate={navigate}
        onAnalysisDone={(res) => {
          setLatestResult(res)
          sessionStorage.setItem("medisense_latest_result", JSON.stringify(res))
        }}
        onProfileUpdate={setProfile}
        profile={profile}
      />
    )
  }

  if (route === "/results") {
    if (!latestResult) {
      // If no result exists in state or sessionStorage, redirect to /home
      navigate("/home")
      return null
    }

    return (
      <>
        <ResultsPage
          onNewAnalysis={() => navigate("/home")}
          onProfile={() => setProfileOpen(true)}
          profile={profile}
          result={latestResult}
        />
        {profileOpen && (
          <ProfileDrawer
            onClose={() => setProfileOpen(false)}
            onLogout={() => {
              sessionStorage.removeItem("medisense_token")
              sessionStorage.removeItem("medisense_user")
              sessionStorage.removeItem("medisense_latest_result")
              setLatestResult(null)
              navigate("/login")
            }}
            onUpdate={setProfile}
            profile={profile}
          />
        )}
      </>
    )
  }

  return <Landing navigate={navigate} />
}
