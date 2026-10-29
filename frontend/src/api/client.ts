import axios, { AxiosProgressEvent } from "axios"
import { AuthResponse, JobResponse, PredictionResult, UserProfile } from "./types"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

export const apiClient = axios.create({
  baseURL: API_BASE,
})

// Attach Bearer token from sessionStorage
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("medisense_token")
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Global 401 interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      sessionStorage.removeItem("medisense_token")
      sessionStorage.removeItem("medisense_user")
      window.dispatchEvent(new Event("medisense_unauthorized"))
    }
    return Promise.reject(error)
  }
)

export const api = {
  // Job Flow
  async createJob(
    module: string,
    file: File,
    onUploadProgress?: (progressEvent: AxiosProgressEvent) => void,
    roiBox?: number[] | null
  ): Promise<{ job_id: string; status: string }> {
    const formData = new FormData()
    formData.append("module", module)
    formData.append("file", file)
    if (roiBox && roiBox.length === 4) {
      formData.append("roi_box", JSON.stringify(roiBox))
    }

    const resp = await apiClient.post<{ job_id: string; status: string }>(
      "/api/jobs",
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress,
      }
    )
    return resp.data
  },

  async getJobStatus(jobId: string): Promise<JobResponse> {
    const resp = await apiClient.get<JobResponse>(`/api/jobs/${jobId}`)
    return resp.data
  },

  getReportImageUrl(reportId: string): string {
    const token = sessionStorage.getItem("medisense_token")
    if (token) {
      return `${API_BASE}/api/report/${reportId}/image?token=${encodeURIComponent(token)}`
    }
    return `${API_BASE}/api/report/${reportId}/image`
  },

  async getReportImageBlob(reportId: string): Promise<Blob> {
    const resp = await apiClient.get(`/api/report/${reportId}/image`, {
      responseType: "blob",
    })
    return resp.data
  },

  async downloadReportPdf(reportId: string): Promise<void> {
    const resp = await apiClient.get(`/api/report/${reportId}/pdf`, {
      responseType: "blob",
    })
    const url = window.URL.createObjectURL(new Blob([resp.data], { type: "application/pdf" }))
    const link = document.createElement("a")
    link.href = url
    link.setAttribute("download", `MediSense_Report_${reportId}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  // Auth & Profile
  async register(data: {
    name: string
    age: number
    sex: string
    contact: string
    email: string
    password: string
  }): Promise<AuthResponse> {
    const resp = await apiClient.post<AuthResponse>("/api/auth/register", data)
    return resp.data
  },

  async login(data: { email: string; password: string }): Promise<AuthResponse> {
    const resp = await apiClient.post<AuthResponse>("/api/auth/login", data)
    return resp.data
  },

  async getMe(): Promise<UserProfile> {
    const resp = await apiClient.get<UserProfile>("/api/me")
    return resp.data
  },

  async updateMe(data: Partial<UserProfile>): Promise<UserProfile> {
    const resp = await apiClient.put<UserProfile>("/api/me", data)
    return resp.data
  },

  async updatePassword(data: { current_password: string; new_password: string }): Promise<{ message: string }> {
    const resp = await apiClient.put<{ message: string }>("/api/me/password", data)
    return resp.data
  },

  async uploadAvatar(file: File): Promise<UserProfile> {
    const formData = new FormData()
    formData.append("file", file)
    const resp = await apiClient.post<UserProfile>("/api/me/avatar", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    return resp.data
  },

  getAvatarUrl(): string {
    return `${API_BASE}/api/me/avatar?t=${Date.now()}`
  },
}
