import Navbar from "./navbar"

interface PageShellProps {
  children: React.ReactNode
  maxWidth?: number | string
  className?: string
}

export default function PageShell({ children, maxWidth = 1140, className }: PageShellProps) {
  return (
    <>
      <Navbar />
      <main style={{
        maxWidth,
        margin: "0 auto",
        padding: "32px 24px 64px",
      }} className={className}>
        {children}
      </main>
    </>
  )
}
