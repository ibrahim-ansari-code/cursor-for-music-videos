'use client'

import { useState, useRef } from 'react'
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
  Palette,
  Upload,
  X,
  FileAudio,
  FileImage,
  AlertCircle
} from 'lucide-react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const logoUrl = "/logo.png";
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'uploading' | 'processing' | 'complete' | 'error'>('idle')
  const [progress, setProgress] = useState(0)
  const [statusMessage, setStatusMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  
  const audioInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)

  const handleAudioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setAudioFile(file)
    }
  }

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setImageFile(file)
      // Create preview URL
      const previewUrl = URL.createObjectURL(file)
      setImagePreview(previewUrl)
    }
  }

  const removeAudioFile = () => {
    setAudioFile(null)
    if (audioInputRef.current) {
      audioInputRef.current.value = ''
    }
  }

  const removeImageFile = () => {
    setImageFile(null)
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview)
      setImagePreview(null)
    }
    if (imageInputRef.current) {
      imageInputRef.current.value = ''
    }
  }

  const handleGenerate = async () => {
    if (!audioFile || !imageFile) return
    
    setIsGenerating(true)
    setGenerationStatus('uploading')
    setProgress(0)
    setStatusMessage('Uploading files...')
    setErrorMessage('')

    try {
      // Upload files to backend
      const formData = new FormData()
      formData.append('audio', audioFile)
      formData.append('image', imageFile)

      const uploadResponse = await fetch(`${API_BASE_URL}/uploads/`, {
        method: 'POST',
        body: formData,
      })

      if (!uploadResponse.ok) {
        const error = await uploadResponse.json()
        throw new Error(error.detail || 'Upload failed')
      }

      const uploadData = await uploadResponse.json()
      setProgress(20)
      setGenerationStatus('processing')
      setStatusMessage('Creating video generation job...')

      // Create job with the uploaded file URLs
      const jobResponse = await fetch(`${API_BASE_URL}/jobs/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          audio_url: uploadData.audio_url,
          image_url: uploadData.image_url,
        }),
      })

      if (!jobResponse.ok) {
        throw new Error('Failed to create job')
      }

      const jobData = await jobResponse.json()
      setProgress(30)
      setStatusMessage('Generating your music video...')

      // Poll for job status
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`${API_BASE_URL}/jobs/${jobData.job_id}`)
          const statusData = await statusResponse.json()

          if (statusData.status === 'done') {
            clearInterval(pollInterval)
            setProgress(100)
            setGenerationStatus('complete')
            setIsGenerating(false)
            if (statusData.video_url) {
              setVideoUrl(statusData.video_url)
            }
          } else if (statusData.status === 'failed') {
            clearInterval(pollInterval)
            throw new Error(statusData.error || 'Video generation failed')
          } else {
            // Update progress based on status
            const progressMap: Record<string, number> = {
              'queued': 30,
              'running': 50,
              'generating_scenes': 70,
              'composing': 90,
            }
            setProgress(progressMap[statusData.status] || statusData.progress * 100)
            setStatusMessage(statusData.message || 'Processing...')
          }
        } catch (error) {
          console.error('Error polling status:', error)
        }
      }, 2000)

      // For now, simulate completion after some time (remove this when backend is fully implemented)
      setTimeout(() => {
        clearInterval(pollInterval)
        setProgress(100)
        setGenerationStatus('complete')
        setIsGenerating(false)
        // Demo video URL - replace with actual video URL when backend is ready
        setVideoUrl('https://www.w3schools.com/html/mov_bbb.mp4')
      }, 8000)

    } catch (error) {
      console.error('Generation error:', error)
      
      // Check if it's a network error (backend not running)
      const isNetworkError = error instanceof TypeError && error.message.includes('fetch')
      
      if (isNetworkError) {
        // Fallback to demo mode when backend is not available
        console.log('Backend not available, running in demo mode...')
        setGenerationStatus('processing')
        setStatusMessage('Demo mode: Simulating video generation...')
        
        // Simulate generation progress
        let currentProgress = 0
        const interval = setInterval(() => {
          currentProgress += Math.random() * 15
          if (currentProgress >= 100) {
            clearInterval(interval)
            setProgress(100)
            setGenerationStatus('complete')
            setIsGenerating(false)
            // Demo video URL for fallback mode
            setVideoUrl('https://www.w3schools.com/html/mov_bbb.mp4')
          } else {
            setProgress(currentProgress)
            // Update status message based on progress
            if (currentProgress < 30) {
              setStatusMessage('Analyzing audio waveforms...')
            } else if (currentProgress < 60) {
              setStatusMessage('Generating visual scenes...')
            } else if (currentProgress < 90) {
              setStatusMessage('Composing final video...')
            } else {
              setStatusMessage('Finalizing...')
            }
          }
        }, 500)
      } else {
        // Show error to user
        setGenerationStatus('error')
        setIsGenerating(false)
        setErrorMessage(error instanceof Error ? error.message : 'An error occurred during generation')
      }
    }
  }

  const isFormValid = audioFile !== null && imageFile !== null

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
            Upload your audio and an image. Generate stunning music videos.
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
              {/* Audio File Upload */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
                  <div className="w-6 h-6 bg-gray-100 rounded-none flex items-center justify-center">
                    <Headphones className="w-3.5 h-3.5 text-gray-600" />
                  </div>
                  Audio File
                </label>
                <input
                  ref={audioInputRef}
                  type="file"
                  accept="audio/mpeg,audio/mp3,audio/wav,audio/x-wav,audio/m4a,.mp3,.wav,.m4a"
                  onChange={handleAudioChange}
                  className="hidden"
                  id="audio-upload"
                />
                {audioFile ? (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-none"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-100 rounded-none flex items-center justify-center">
                        <FileAudio className="w-5 h-5 text-green-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900 truncate max-w-[200px]">
                          {audioFile.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {(audioFile.size / (1024 * 1024)).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={removeAudioFile}
                      className="p-2 hover:bg-green-100 rounded-none transition-colors"
                    >
                      <X className="w-4 h-4 text-gray-500" />
                    </button>
                  </motion.div>
                ) : (
                  <label
                    htmlFor="audio-upload"
                    className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-200 rounded-none cursor-pointer hover:border-gray-300 hover:bg-gray-50 transition-all"
                  >
                    <Upload className="w-8 h-8 text-gray-400 mb-2" />
                    <span className="text-sm text-gray-600">Click to upload audio</span>
                    <span className="text-xs text-gray-400 mt-1">MP3, WAV, or M4A</span>
                  </label>
                )}
                <p className="text-xs text-gray-400 mt-2">Upload the audio file for your music video</p>
              </div>

              {/* Image File Upload */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3">
                  <div className="w-6 h-6 bg-gray-100 rounded-none flex items-center justify-center">
                    <ImageIcon className="w-3.5 h-3.5 text-gray-600" />
                  </div>
                  Image File
                </label>
                <input
                  ref={imageInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/webp,.png,.jpg,.jpeg,.webp"
                  onChange={handleImageChange}
                  className="hidden"
                  id="image-upload"
                />
                {imageFile ? (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="relative"
                  >
                    <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-none">
                      <div className="flex items-center gap-3">
                        {imagePreview ? (
                          <div className="w-16 h-16 rounded-none overflow-hidden border border-green-200">
                            <img
                              src={imagePreview}
                              alt="Preview"
                              className="w-full h-full object-cover"
                            />
                          </div>
                        ) : (
                          <div className="w-10 h-10 bg-green-100 rounded-none flex items-center justify-center">
                            <FileImage className="w-5 h-5 text-green-600" />
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-medium text-gray-900 truncate max-w-[200px]">
                            {imageFile.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {(imageFile.size / (1024 * 1024)).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={removeImageFile}
                        className="p-2 hover:bg-green-100 rounded-none transition-colors"
                      >
                        <X className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                  </motion.div>
                ) : (
                  <label
                    htmlFor="image-upload"
                    className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-200 rounded-none cursor-pointer hover:border-gray-300 hover:bg-gray-50 transition-all"
                  >
                    <Upload className="w-8 h-8 text-gray-400 mb-2" />
                    <span className="text-sm text-gray-600">Click to upload image</span>
                    <span className="text-xs text-gray-400 mt-1">PNG, JPG, or WebP</span>
                  </label>
                )}
                <p className="text-xs text-gray-400 mt-2">Upload an image that will inspire the video style</p>
              </div>

              {/* Divider */}
              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-100" />
                </div>
              </div>

              {/* Generate Button */}
              <AnimatePresence mode="wait">
                {generationStatus === 'error' ? (
                  <motion.div
                    key="error"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-center py-6"
                  >
                    <div className="w-16 h-16 bg-red-100 rounded-none flex items-center justify-center mx-auto mb-4">
                      <AlertCircle className="w-8 h-8 text-red-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Generation Failed</h3>
                    <p className="text-red-600 text-sm mb-4">{errorMessage}</p>
                    <button 
                      onClick={() => {
                        setGenerationStatus('idle')
                        setErrorMessage('')
                      }}
                      className="btn-secondary"
                    >
                      Try Again
                    </button>
                  </motion.div>
                ) : (generationStatus === 'uploading' || generationStatus === 'processing') ? (
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
                        {generationStatus === 'uploading' ? 'Uploading files...' : 'Generating your music video...'}
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
                      {generationStatus === 'uploading' ? (
                        <>
                          <Upload className="w-3.5 h-3.5" />
                          Uploading your audio and image files...
                        </>
                      ) : (
                        <>
                          <Wand2 className="w-3.5 h-3.5" />
                          {statusMessage || 'AI is analyzing your audio and generating frames...'}
                        </>
                      )}
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
                    
                    {/* Video Player */}
                    {videoUrl && (
                      <div className="mb-6">
                        <div className="aspect-video bg-black rounded-lg overflow-hidden shadow-lg">
                          <video
                            src={videoUrl}
                            controls
                            autoPlay
                            className="w-full h-full"
                          >
                            Your browser does not support the video tag.
                          </video>
                        </div>
                        <div className="mt-3 flex justify-center">
                          <a
                            href={videoUrl}
                            download="music-video.mp4"
                            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 transition-colors"
                          >
                            <ArrowRight className="w-3.5 h-3.5" />
                            Download Video
                          </a>
                        </div>
                      </div>
                    )}
                    
                    <button 
                      onClick={() => {
                        setGenerationStatus('idle')
                        setProgress(0)
                        setAudioFile(null)
                        setImageFile(null)
                        setImagePreview(null)
                        setStatusMessage('')
                        setVideoUrl(null)
                        if (audioInputRef.current) audioInputRef.current.value = ''
                        if (imageInputRef.current) imageInputRef.current.value = ''
                      }}
                      className="btn-secondary"
                    >
                      Create Another
                    </button>
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
