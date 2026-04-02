import { HeadsetIcon } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SupportForm } from "@/components/support-form";

export const Index = () => {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-lg space-y-6">
        {/* Branding */}
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            CloudStream CRM
          </h1>
          <p className="text-sm text-muted-foreground">
            Creative Flow, Automated Operations.
          </p>
        </div>

        {/* Form Card */}
        <Card>
          <CardHeader className="space-y-1">
            <div className="flex items-center gap-2">
              <HeadsetIcon className="h-5 w-5 text-primary" />
              <CardTitle className="text-xl">Contact Support</CardTitle>
            </div>
            <CardDescription>
              Fill out the form below and our team will get back to you within 24 hours.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SupportForm />
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground">
          We typically respond within one business day. For urgent issues, please include
          your account ID in the subject line.
        </p>
      </div>
    </main>
  );
};

