import Compressor from 'compressorjs';
import imageCompression from 'browser-image-compression';
import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile, toBlobURL } from '@ffmpeg/util';

// Image Compression using Compressor.js
export const compressImage = (file, quality = 0.8, maxWidth = 1920, maxHeight = 1080) => {
  return new Promise((resolve, reject) => {
    new Compressor(file, {
      quality,
      maxWidth,
      maxHeight,
      mimeType: 'image/jpeg',
      convertTypes: 'image/webp', // Convert to WebP when possible
      success: resolve,
      error: reject,
    });
  });
};

// Alternative image compression using browser-image-compression
export const compressImageAdvanced = async (file, options = {}) => {
  const defaultOptions = {
    maxSizeMB: 1,          // Maximum file size in MB
    maxWidthOrHeight: 1920, // Maximum width or height
    useWebWorker: true,     // Use web worker for better performance
    quality: 0.8,           // Quality (0-1)
    initialQuality: 0.8,    // Initial quality
  };
  
  const mergedOptions = { ...defaultOptions, ...options };
  
  try {
    const compressedFile = await imageCompression(file, mergedOptions);
    return compressedFile;
  } catch (error) {
    console.error('Image compression failed:', error);
    throw error;
  }
};

// FFmpeg instance for video compression
let ffmpeg = null;

// Initialize FFmpeg
export const initFFmpeg = async () => {
  if (ffmpeg) return ffmpeg;
  
  try {
    ffmpeg = new FFmpeg();
    
    // Load FFmpeg with proper CORS handling
    const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.10/dist/esm';
    
    await ffmpeg.load({
      coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
      wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
    });
    
    console.log('✅ FFmpeg loaded successfully');
    return ffmpeg;
  } catch (error) {
    console.error('❌ FFmpeg initialization failed:', error);
    throw error;
  }
};

// Video compression using FFmpeg
export const compressVideo = async (file, options = {}) => {
  const {
    quality = 28,      // CRF value (18-28 is good range, lower = better quality)
    scale = '720:-2',  // Scale to 720p width, auto height
    format = 'mp4'     // Output format
  } = options;
  
  try {
    console.log('🎬 Starting video compression...');
    
    // Initialize FFmpeg if not done already
    const ffmpegInstance = await initFFmpeg();
    
    // Generate unique filenames
    const inputName = `input_${Date.now()}.${file.name.split('.').pop()}`;
    const outputName = `output_${Date.now()}.${format}`;
    
    // Write input file to FFmpeg filesystem
    await ffmpegInstance.writeFile(inputName, await fetchFile(file));
    
    // Compression command
    await ffmpegInstance.exec([
      '-i', inputName,
      '-c:v', 'libx264',     // H.264 codec
      '-crf', quality.toString(), // Quality setting
      '-vf', `scale=${scale}`,    // Scale video
      '-c:a', 'aac',         // Audio codec
      '-b:a', '128k',        // Audio bitrate
      '-preset', 'medium',   // Encoding speed vs quality
      '-movflags', '+faststart', // Optimize for web streaming
      outputName
    ]);
    
    // Read compressed file
    const data = await ffmpegInstance.readFile(outputName);
    
    // Clean up files
    await ffmpegInstance.deleteFile(inputName);
    await ffmpegInstance.deleteFile(outputName);
    
    // Create blob from compressed data
    const compressedBlob = new Blob([data], { type: `video/${format}` });
    
    // Create File object with original name but compressed content
    const compressedFile = new File([compressedBlob], file.name, {
      type: `video/${format}`,
      lastModified: Date.now()
    });
    
    console.log('✅ Video compression completed');
    console.log(`📊 Original size: ${(file.size / 1024 / 1024).toFixed(2)}MB`);
    console.log(`📊 Compressed size: ${(compressedFile.size / 1024 / 1024).toFixed(2)}MB`);
    
    return compressedFile;
  } catch (error) {
    console.error('❌ Video compression failed:', error);
    throw error;
  }
};

// Get compression recommendations based on file size
export const getCompressionRecommendations = (file) => {
  const sizeInMB = file.size / (1024 * 1024);
  const isImage = file.type.startsWith('image/');
  const isVideo = file.type.startsWith('video/');
  
  if (isImage) {
    if (sizeInMB > 10) {
      return {
        shouldCompress: true,
        reason: 'Image is larger than 10MB',
        recommendedSettings: { quality: 0.6, maxWidth: 1920, maxHeight: 1080 }
      };
    } else if (sizeInMB > 5) {
      return {
        shouldCompress: true,
        reason: 'Image is larger than 5MB',
        recommendedSettings: { quality: 0.7, maxWidth: 1920, maxHeight: 1080 }
      };
    }
  }
  
  if (isVideo) {
    if (sizeInMB > 30) {
      return {
        shouldCompress: true,
        reason: 'Video is larger than 30MB',
        recommendedSettings: { quality: 32, scale: '480:-2' } // Lower quality
      };
    } else if (sizeInMB > 15) {
      return {
        shouldCompress: true,
        reason: 'Video is larger than 15MB',
        recommendedSettings: { quality: 28, scale: '720:-2' } // Standard quality
      };
    }
  }
  
  return {
    shouldCompress: false,
    reason: 'File size is acceptable',
    recommendedSettings: null
  };
};

// Utility to format file size
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};