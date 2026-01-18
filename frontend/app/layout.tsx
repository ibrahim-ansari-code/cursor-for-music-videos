import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Transform Audio Into Visual Art | MeloVue',
  description: 'Transform your audio and images into stunning AI-generated music videos',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  )
}
