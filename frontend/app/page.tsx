'use client'

import { useState } from 'react'
import Image from 'next/image'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Music, 
  Image as ImageIcon, 
  Sparkles, 
  Play, 
  Wand2, 
  Headphones, 
  CheckCircle2,
  Loader2,
  ArrowRight,
  Zap,
  Film,
  Palette
} from 'lucide-react'

export default function Home() {
  const logoUrl = "/logo.png";
  const [audioUrl, setAudioUrl] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'processing' | 'complete'>('idle')
  const [progress, setProgress] = useState(0)

  const handleGenerate = async () => {
    if (!audioUrl || !imageUrl) return
    
    setIsGenerating(true)
    setGenerationStatus('processing')
    setProgress(0)

    // Simulate generation progress
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          setGenerationStatus('complete')
          setIsGenerating(false)
          return 100
        }
        return prev + Math.random() * 15
      })
    }, 500)
  }

  const isFormValid = audioUrl.trim() !== '' && imageUrl.trim() !== ''

  return (
    <div className="min-h-screen bg-[#fafafa] relative overflow-hidden">
      {/* Logos */}
      <div className="absolute top-6 left-6 z-50">
        <span className="text-xl font-semibold tracking-tight text-[#3a5a40]">MeloVue</span>
      </div>
      <div className="absolute bottom-6 left-6 z-50">
        <span className="text-base font-semibold tracking-tight text-[#3a5a40]/50">MeloVue</span>
      </div>

      {/* Subtle background pattern */}
      <div className="absolute inset-0 opacity-[0.015]">
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, #000 1px, transparent 0)`,
          backgroundSize: '32px 32px'
        }} />
      </div>

      {/* Gradient orbs */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-green-200/30 rounded-none blur-[120px] -translate-y-1/2" />
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-emerald-100/40 rounded-none blur-[100px] translate-y-1/2" />

      {/* Hero Section */}
      <main className="relative z-10 max-w-6xl mx-auto px-6 pt-20 pb-32">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-center mb-16"
        >
          <h1 className="font-serif text-5xl md:text-7xl font-medium text-gray-900 mb-6 leading-[1.1] tracking-tight">
            Transform Audio<br />
            <span className="italic text-gray-500">Into Visual Art</span>
          </h1>
          
          <p className="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed">
            Paste your links. Upload your sound. Generate stunning videos.
          </p>
        </motion.div>

        {/* Main Card */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="max-w-2xl mx-auto"
        >
          <div className="card p-8 md:p-10 relative overflow-hidden">
            {/* Subtle gradient overlay */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-green-50 to-transparent rounded-none opacity-50" />
            
            <div className="relative z-10 space-y-6">
              {/* Audio URL Input */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
                  <div className="w-6 h-6 bg-gray-100 rounded-none flex items-center justify-center">
                    <Headphones className="w-3.5 h-3.5 text-gray-600" />
                  </div>
                  Audio URL
                </label>
                <div className="relative">
                  <input
                    type="url"
                    placeholder="https://example.com/your-song.mp3"
                    value={audioUrl}
                    onChange={(e) => setAudioUrl(e.target.value)}
                    className="input-elegant pr-12"
                  />
                  {audioUrl && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="absolute right-4 top-1/2 -translate-y-1/2"
                    >
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    </motion.div>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-2">Paste a direct link to an MP3 audio file containing your song</p>
              </div>

              {/* Image URL Input */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
                  <div className="w-6 h-6 bg-gray-100 rounded-none flex items-center justify-center">
                    <ImageIcon className="w-3.5 h-3.5 text-gray-600" />
                  </div>
                  Image URL
                </label>
                <div className="relative">
                  <input
                    type="url"
                    placeholder="https://example.com/your-image.jpg"
                    value={imageUrl}
                    onChange={(e) => setImageUrl(e.target.value)}
                    className="input-elegant pr-12"
                  />
                  {imageUrl && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="absolute right-4 top-1/2 -translate-y-1/2"
                    >
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    </motion.div>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-2">Paste a direct link to an image that will inspire the video style</p>
              </div>

              {/* Divider */}
              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-100" />
                </div>
              </div>

              {/* Generate Button */}
              <AnimatePresence mode="wait">
                {generationStatus === 'processing' ? (
                  <motion.div
                    key="processing"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="space-y-4"
                  >
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600 flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Generating your music video...
                      </span>
                      <span className="text-gray-900 font-medium">{Math.min(Math.round(progress), 100)}%</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-none overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-green-500 to-emerald-500 rounded-none"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ ease: "linear" }}
                      />
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <Wand2 className="w-3.5 h-3.5" />
                      AI is analyzing your audio and generating frames...
                    </div>
                  </motion.div>
                ) : generationStatus === 'complete' ? (
                  <motion.div
                    key="complete"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-center py-6"
                  >
                    <div className="w-16 h-16 bg-green-100 rounded-none flex items-center justify-center mx-auto mb-4">
                      <CheckCircle2 className="w-8 h-8 text-green-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Video Generated Successfully!</h3>
                    <p className="text-gray-500 text-sm mb-4">Your AI music video is ready to view</p>
                    <div className="flex gap-3 justify-center">
                      <button className="btn-primary flex items-center gap-2">
                        <Play className="w-4 h-4" />
                        Watch Video
                      </button>
                      <button 
                        onClick={() => {
                          setGenerationStatus('idle')
                          setProgress(0)
                        }}
                        className="btn-secondary"
                      >
                        Create Another
                      </button>
                    </div>
                  </motion.div>
                ) : (
                  <motion.button
                    key="generate"
                    onClick={handleGenerate}
                    disabled={!isFormValid || isGenerating}
                    className={`w-full py-4 rounded-none font-medium text-base flex items-center justify-center gap-3 transition-all duration-300 ${
                      isFormValid
                        ? 'bg-gray-900 text-white hover:bg-gray-800 hover:shadow-lg hover:shadow-gray-900/20 active:scale-[0.99]'
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    }`}
                    whileHover={isFormValid ? { scale: 1.01 } : {}}
                    whileTap={isFormValid ? { scale: 0.99 } : {}}
                  >
                    <Sparkles className="w-5 h-5" />
                    Generate Music Video
                    <ArrowRight className="w-4 h-4" />
                  </motion.button>
                )}
              </AnimatePresence>
            </div>
          </div>
        </motion.div>

        {/* Features Section */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="grid md:grid-cols-3 gap-6 mt-20"
        >
          {[
            {
              icon: Film,
              title: 'Cinematic Quality',
              description: 'Generate high-quality visuals that sync perfectly with your audio beats.'
            },
            {
              icon: Palette,
              title: 'Style Transfer',
              description: 'Your image sets the visual tone. Our AI extracts style and applies it throughout the video.'
            },
            {
              icon: Zap,
              title: 'Fast Generation',
              description: 'Advanced AI processing delivers your music video in minutes, not hours.'
            }
          ].map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + index * 0.1 }}
              className="card p-6 hover:shadow-md transition-shadow duration-300"
            >
              <div className="w-10 h-10 bg-gray-100 rounded-none flex items-center justify-center mb-4">
                <feature.icon className="w-5 h-5 text-gray-700" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{feature.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{feature.description}</p>
            </motion.div>
          ))}
        </motion.div>

      </main>
    </div>
  )
}
