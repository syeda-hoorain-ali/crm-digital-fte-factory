"use client"

import { useState } from "react";
import { Loader2Icon, SendIcon } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { MAX_MESSAGE_LENGTH, supportFormSchema, type SupportFormValues } from "@/features/support-form/schema";
import { useSupportForm } from "@/features/support-form/hooks";

export function SupportForm() {
  const [ticketId, setTicketId] = useState<string | null>(null);
  const {
    submitSupportRequest: { mutateAsync: submitSupportRequest, isPending: isSubmitting, error }
  } = useSupportForm();

  const form = useForm<SupportFormValues>({
    resolver: zodResolver(supportFormSchema),
    defaultValues: {
      name: "",
      email: "",
      phone: "",
      subject: "",
      category: "general",
      priority: "medium",
      message: "",
    },
  });

  const messageValue = form.watch("message");
  const remainingChars = MAX_MESSAGE_LENGTH - (messageValue?.length ?? 0);

  const onSubmit = async (data: SupportFormValues) => {
    const response = await submitSupportRequest(data, {
      onSuccess() {
        setTicketId(response.ticket_id)
        form.reset()
      }
    })
  }

  if (ticketId) {
    return (
      <Card className="p-6 max-w-2xl mx-auto">
        <div className="text-center space-y-4">
          <div className="text-6xl">✓</div>
          <h2 className="text-xl font-bold">Request Submitted Successfully</h2>
          <p className="text-sm text-muted-foreground">
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
              form.reset()
            }}
            variant="outline"
            className="cursor-pointer"
          >
            Submit Another Request
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <FieldGroup>
        <Controller
          name="name"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={`support-form-${field.name}`}>
                Name <span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                {...field}
                placeholder="Your full name"
                id={`support-form-${field.name}`}
                aria-invalid={fieldState.invalid}
                autoComplete="off"
                disabled={isSubmitting}
              />
              {fieldState.invalid && (
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />


        <Controller
          name="email"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={`support-form-${field.name}`}>
                Email <span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                {...field}
                type="email"
                placeholder="you@example.com"
                id={`support-form-${field.name}`}
                aria-invalid={fieldState.invalid}
                autoComplete="off"
                disabled={isSubmitting}
              />
              {fieldState.invalid && (
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />

        <Controller
          name="phone"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={`support-form-${field.name}`}>
                Phone <span className="text-muted-foreground text-xs">(Optional)</span>
              </FieldLabel>
              <Input
                {...field}
                placeholder="+1 (555) 000-0000"
                id={`support-form-${field.name}`}
                aria-invalid={fieldState.invalid}
                autoComplete="off"
                disabled={isSubmitting}
              />
              {fieldState.invalid && (
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />


        <Controller
          name="subject"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={`support-form-${field.name}`}>
                Subject <span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                {...field}
                placeholder="How can we help?"
                id={`support-form-${field.name}`}
                aria-invalid={fieldState.invalid}
                autoComplete="off"
                disabled={isSubmitting}
              />
              {fieldState.invalid && (
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Controller
            name="category"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor={`support-form-${field.name}`}>
                  Category <span className="text-destructive">*</span>
                </FieldLabel>
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  disabled={isSubmitting}
                >
                  <SelectTrigger id={`support-form-${field.name}`} aria-invalid={fieldState.invalid}>
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="general">General</SelectItem>
                    <SelectItem value="technical">Technical</SelectItem>
                    <SelectItem value="billing">Billing</SelectItem>
                    <SelectItem value="feedback">Feedback</SelectItem>
                    <SelectItem value="bug_report">Bug Report</SelectItem>
                  </SelectContent>
                </Select>
                {fieldState.invalid && (
                  <FieldError errors={[fieldState.error]} />
                )}
              </Field>
            )}
          />

          <Controller
            name="priority"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor={`support-form-${field.name}`}>
                  Priority <span className="text-destructive">*</span>
                </FieldLabel>
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  disabled={isSubmitting}
                >
                  <SelectTrigger id={`support-form-${field.name}`} aria-invalid={fieldState.invalid}>
                    <SelectValue placeholder="Select priority level" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
                {fieldState.invalid && (
                  <FieldError errors={[fieldState.error]} />
                )}
              </Field>
            )}
          />
        </div>


        <Controller
          name="message"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor={`support-form-${field.name}`}>
                Message <span className="text-destructive">*</span>
              </FieldLabel>
              <Textarea
                {...field}
                placeholder="Describe your issue or question in detail..."
                className="min-h-30 resize-y"
                id={`support-form-${field.name}`}
                aria-invalid={fieldState.invalid}
                autoComplete="off"
                disabled={isSubmitting}
              />
              <div className="flex items-center justify-between">
                {fieldState.invalid && (
                  <FieldError errors={[fieldState.error]} />
                )}
                <span
                  className={`ml-auto text-xs ${remainingChars < 0
                    ? "text-destructive"
                    : remainingChars < 100
                      ? "text-muted-foreground"
                      : "text-muted-foreground/60"
                    }`}
                >
                  {remainingChars} characters remaining
                </span>
              </div>
            </Field>
          )}
        />
      </FieldGroup>

      {error &&
        <div
          role="alert"
          data-slot="field-error"
          className="text-sm font-normal text-destructive mb-2 -mt-3"
        >
          {error.message}
        </div>
      }

      <Button type="submit" className="w-full cursor-pointer" disabled={isSubmitting}>
        {isSubmitting ? (
          <>
            <Loader2Icon className="animate-spin" />
            Sending...
          </>
        ) : (
          <>
            <SendIcon />
            Send Message
          </>
        )}
      </Button>
    </form>
  )
}
