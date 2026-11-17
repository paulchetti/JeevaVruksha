import "./styles.css";

export const metadata = { title: "Jeeva Vruksha", description: "Clinical simulation for MBBS emergency training" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
