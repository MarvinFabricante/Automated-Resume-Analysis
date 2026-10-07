import React from 'react';
import { AlertTriangle, RefreshCw, Home, LogOut } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  handleClearAndReset = () => {
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch {
      // ignore
    }
    window.location.href = '/login';
  };

  render() {
    if (this.state.hasError) {
      const errorMessage = this.state.error?.message || "An unexpected application error occurred.";

      return (
        <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center p-6 font-['Inter',_sans-serif]">
          <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xl shadow-slate-200/50 max-w-lg w-full p-8 text-center animate-in zoom-in-95 duration-300">
            <div className="w-16 h-16 bg-red-50 text-[#D60041] rounded-2xl flex items-center justify-center mx-auto mb-6 border border-red-100 shadow-sm">
              <AlertTriangle size={32} />
            </div>

            <h2 className="text-2xl font-black text-slate-900 mb-2 tracking-tight">
              Application Encountered an Error
            </h2>
            <p className="text-slate-500 text-sm mb-6 leading-relaxed">
              We encountered an unexpected issue while rendering this page. You can try refreshing the page or clearing the local session.
            </p>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-left mb-6 overflow-hidden">
              <p className="text-xs font-mono text-slate-700 break-words font-semibold line-clamp-3">
                {errorMessage}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 justify-center mb-4">
              <button
                onClick={this.handleReload}
                className="bg-[#D60041] hover:bg-[#b00035] text-white px-5 py-3 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-lg shadow-pink-100 active:scale-95"
              >
                <RefreshCw size={14} /> Refresh Page
              </button>
              <button
                onClick={this.handleGoHome}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-5 py-3 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-95"
              >
                <Home size={14} /> Return Home
              </button>
            </div>

            <button
              onClick={this.handleClearAndReset}
              className="text-xs text-slate-400 hover:text-slate-600 transition-colors flex items-center justify-center gap-1.5 mx-auto font-medium"
            >
              <LogOut size={12} /> Clear Session & Login Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
