import React, { useRef, useState } from 'react';
import { Button } from '../../components/Button';

export interface ShareCardData {
  headline: string;
  keyNumber: string;
  placeName: string;
  sourceLine: string;
  issuedAt: string;
  caveat?: string;
}

interface ShareModalProps {
  data: ShareCardData;
  isOpen: boolean;
  onClose: () => void;
}

export const ShareModal: React.FC<ShareModalProps> = ({ data, isOpen, onClose }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const shareUrl = `${window.location.origin}/?place=${encodeURIComponent(data.placeName)}`;
  const shareText = `${data.headline} (${data.keyNumber}) for ${data.placeName} | ${data.sourceLine} via WeatherGPT`;

  const handleShareLink = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `WeatherGPT: ${data.headline}`,
          text: shareText,
          url: shareUrl,
        });
        return;
      } catch {
        // user cancelled or failed, fallback to copy
      }
    }

    try {
      await navigator.clipboard.writeText(`${shareText}\n${shareUrl}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      alert('Could not copy to clipboard.');
    }
  };

  const handleDownloadImageCard = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Dimensions: 600 x 340 (Social Card)
    canvas.width = 600;
    canvas.height = 340;

    // Background gradient
    const grad = ctx.createLinearGradient(0, 0, 600, 340);
    grad.addColorStop(0, '#1E293B');
    grad.addColorStop(1, '#0F172A');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 600, 340);

    // Decorative pill
    ctx.fillStyle = '#1B7F3B';
    ctx.beginPath();
    ctx.roundRect(40, 30, 130, 28, 14);
    ctx.fill();

    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 12px "Noto Sans", sans-serif';
    ctx.fillText('WeatherGPT Pilot', 55, 49);

    // Place
    ctx.fillStyle = '#94A3B8';
    ctx.font = '14px "Noto Sans", sans-serif';
    ctx.fillText(`Forecast for ${data.placeName}`, 40, 90);

    // Headline
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 24px "Noto Sans", sans-serif';
    ctx.fillText(data.headline, 40, 125);

    // Key number box
    ctx.fillStyle = '#1E3A8A';
    ctx.beginPath();
    ctx.roundRect(40, 150, 140, 56, 12);
    ctx.fill();

    ctx.fillStyle = '#60A5FA';
    ctx.font = 'bold 26px "Noto Sans", sans-serif';
    ctx.fillText(data.keyNumber, 55, 188);

    // Source line & Issued
    ctx.fillStyle = '#94A3B8';
    ctx.font = '12px "Noto Sans", sans-serif';
    ctx.fillText(data.sourceLine, 40, 240);
    ctx.fillText(`Issued: ${data.issuedAt}`, 40, 260);

    if (data.caveat) {
      ctx.fillStyle = '#F59E0B';
      ctx.fillText(`Notice: ${data.caveat}`, 40, 285);
    }

    // Footer non-commercial disclaimer
    ctx.fillStyle = '#64748B';
    ctx.font = '10px "Noto Sans", sans-serif';
    ctx.fillText('Non-commercial public-interest pilot • weathergpt.in', 40, 315);

    // Trigger download
    const link = document.createElement('a');
    link.download = `weathergpt-${data.placeName.toLowerCase()}-forecast.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
    >
      <div className="bg-white dark:bg-slate-900 rounded-spec max-w-md w-full p-6 shadow-xl border border-slate-200 dark:border-slate-800 space-y-5">
        <div className="flex items-center justify-between">
          <h2 id="share-title" className="text-lg font-bold text-slate-900 dark:text-slate-100">
            Share Forecast
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="text-slate-400 hover:text-slate-600 text-lg p-1"
          >
            ✕
          </button>
        </div>

        {/* Preview Card */}
        <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 text-left">
          <span className="text-xs text-blue-600 dark:text-blue-400 font-bold block mb-1">
            {data.placeName}
          </span>
          <h3 className="font-bold text-slate-900 dark:text-slate-100 text-base mb-1">
            {data.headline}
          </h3>
          <span className="text-xl font-black text-blue-700 dark:text-blue-300 block mb-2">
            {data.keyNumber}
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400 block">
            {data.sourceLine}
          </span>
        </div>

        <canvas ref={canvasRef} className="hidden" aria-hidden="true" />

        <div className="flex flex-col sm:flex-row gap-3">
          <Button type="button" variant="primary" onClick={handleShareLink} className="flex-1">
            {copied ? '✓ Link Copied!' : 'Share or Copy Link'}
          </Button>
          <Button type="button" variant="secondary" onClick={handleDownloadImageCard} className="flex-1">
            Save Image Card
          </Button>
        </div>
      </div>
    </div>
  );
};
