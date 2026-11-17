import "./styles.css";
import { AuthProvider } from "../components/auth-provider";

export const metadata = {
  title: "Jeeva Vruksha",
  description: "Clinical simulation for MBBS emergency training",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
