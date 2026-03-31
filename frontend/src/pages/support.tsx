import { Toaster } from "react-hot-toast"
import { SupportForm } from "@/components/support-form"

export default function SupportPage() {
  return (
    <div className="min-h-screen bg-background py-12 px-4">
      <Toaster position="top-right" />
      <SupportForm />
    </div>
  )
}
