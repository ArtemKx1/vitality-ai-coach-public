export function AuthSidePanel() {
  return (
    <div
      className="hidden lg:flex lg:w-5/12 flex-col justify-between p-10 relative overflow-hidden"
      style={{ background: "linear-gradient(180deg, #779bc1 0%, #9abfda 58%, #cbdcec 100%)" }}
    >
      <div
        className="absolute inset-0 opacity-20 pointer-events-none"
        style={{ backgroundImage: "radial-gradient(circle at 50% 0%, #ffffff 0%, transparent 70%)" }}
      />
      <div className="relative z-10 flex flex-col justify-center h-full max-w-md mx-auto text-paper-white">
        <svg className="w-10 h-10 mb-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        </svg>
        <h1 className="font-inter font-semibold text-[44px] leading-[1.1] tracking-[-0.04em] text-paper-white mb-6">
          Precision training,<br />elevated.
        </h1>
        <p className="font-inter text-lg leading-relaxed tracking-[-0.01em] text-paper-white/90 mb-10 max-w-md">
          Connect your Garmin ecosystem to unlock AI-driven insights and professional coaching protocols.
        </p>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-paper-white shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            <span className="font-inter text-sm tracking-[-0.01em]">Secure biometric data encryption</span>
          </div>
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-paper-white shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            <span className="font-inter text-sm tracking-[-0.01em]">Seamless device integration</span>
          </div>
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-paper-white shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            <span className="font-inter text-sm tracking-[-0.01em]">Evidence-based recovery models</span>
          </div>
        </div>
      </div>
    </div>
  )
}
