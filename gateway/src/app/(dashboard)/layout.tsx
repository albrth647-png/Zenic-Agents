import DashboardSidebar from "@/components/dashboard/DashboardSidebar";
import DashboardHeader from "@/components/dashboard/DashboardHeader";
import Providers from "@/components/auth/Providers";
import { RealtimeProvider } from "@/components/dashboard/RealtimeProvider";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <SidebarProvider>
        <RealtimeProvider>
          <DashboardSidebar />
          <SidebarInset>
            <DashboardHeader />
            <div className="flex-1 p-4 sm:p-6">{children}</div>
          </SidebarInset>
        </RealtimeProvider>
      </SidebarProvider>
    </Providers>
  );
}
