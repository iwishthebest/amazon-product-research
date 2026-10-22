import "./globals.css";

export const metadata = {
  title: "AmazonRelease MVP",
  description: "US/AU 竞品选品工作台",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
