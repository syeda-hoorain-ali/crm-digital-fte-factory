"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import toast from "react-hot-toast"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Field } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { supportFormSchema, SupportFormValues } from "@/features/support-form/schema"
import { submitSupportRequest, SupportApiError } from "@/lib/api"

export function SupportForm() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [ticketId, setTicketId] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<SupportFormValues>({
    resolver: zodResolver(supportFormSchema),
    defaultValues: {
      priority: "medium",
      category: "general",
    },
  })

  const onSubmit = async (data: SupportFormValues) => {
    setIsSubmitting(true)
    try {
      const response = await submitSupportRequest(data)
      setTicketId(response.ticket_id)
      toast.success(
        `Support request submitted! Ticket ID: ${response.ticket_id}`,
        { duration: 5000 }
      )
      reset()
    } catch (error) {
      if (error instanceof SupportApiError) {
        toast.error(error.message)
      } else {
        toast.error("An unexpected error occurred. Please try again.")
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  if (ticketId) {
    return (
      <Card className="p-6 max-w-2xl mx-auto">
        <div className="text-center space-y-4">
          <div className="text-6xl">✓</div>
          <h2 className="text-2xl font-bold">Request Submitted Successfully</h2>
          <p className="text-muted-foreground">
            Your support request has been received. We'll get back to you shortly.
          </p>
          <div className="bg-muted p-4 rounded-lg">
            <p className="text-sm font-medium">Your Ticket ID:</p>
            <p className="text-2xl font-mono font-bold">{ticketId}</p>
            <p className="text-xs text-muted-foreground mt-2">
              Save this ID to track your request
            </p>
          </div>
          <Button
            onClick={() => {
              setTicketId(null)
              reset()
            }}
            variant="outline"
          >
            Submit Another Request
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6 max-w-2xl mx-auto">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold">Submit a Support Request</h2>
          <p className="text-muted-foreground">
            Fill out the form below and we'll get back to you as soon as possible.
          </p>
        </div>

        <Field label="Name" error={errors.name?.message} required>
          <Input
            {...register("name")}
            placeholder="Your full name"
            disabled={isSubmitting}
          />
        </Field>

        <Field label="Email" error={errors.email?.message} required>
          <Input
            {...register("email")}
            type="email"
            placeholder="your.email@example.com"
            disabled={isSubmitting}
          />
        </Field>

        <Field label="Subject" error={errors.subject?.message} required>
          <Input
            {...register("subject")}
            placeholder="Brief description of your issue"
            disabled={isSubmitting}
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Category" error={errors.category?.message} required>
            <select
              {...register("category")}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isSubmitting}
            >
              <option value="general">General Inquiry</option>
              <option value="technical">Technical Support</option>
              <option value="billing">Billing Question</option>
              <option value="feedback">Feedback</option>
              <option value="bug_report">Bug Report</option>
            </select>
          </Field>

          <Field label="Priority" error={errors.priority?.message} required>
            <select
              {...register("priority")}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isSubmitting}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </Field>
        </div>

        <Field label="Message" error={errors.message?.message} required>
          <Textarea
            {...register("message")}
            placeholder="Please describe your issue in detail..."
            rows={6}
            disabled={isSubmitting}
          />
        </Field>

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : "Submit Request"}
        </Button>
      </form>
    </Card>
  )
}
