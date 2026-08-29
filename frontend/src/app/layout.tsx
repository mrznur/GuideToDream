import type { Metadata } from "next"
import { Geist } from "next/font/google"
import "./globals.css"
import Navbar from "@/components/layout/navbar"

const geist = Geist({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "GuideToDream — European Masters Intelligence",
  description: "AI-powered personal agent for European Masters programmes and scholarships",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${geist.className} bg-[#05070d] text-white antialiased`}>
        <Navbar />
        {children}
      </body>
    </html>
  )
}
