import React from 'react';
import { Mail, MapPin, Phone } from 'lucide-react';
import logo from '../../assets/logo.png';

const Footer = () => {
  return (
    <footer className="bg-white border-t border-gray-100 pt-16 pb-8 mt-auto">
      <div className="max-w-[1400px] mx-auto px-6 md:px-10">
        <div className="flex flex-col md:flex-row justify-between items-center md:items-start gap-10 mb-12">
          
          {/* Brand Column */}
          <div className="flex flex-col items-center md:items-start max-w-sm">
            <div className="flex items-center gap-3 mb-5">
              <img 
                src={logo} 
                alt="Mariwasa Logo" 
                className="h-10 w-10 object-contain grayscale opacity-80" 
              />
              <span className="text-xl font-black tracking-tight text-gray-900">Mariwasa</span>
            </div>
            <p className="text-sm text-gray-500 font-medium text-center md:text-left leading-relaxed">
              Pioneering excellence in ceramic manufacturing since 1966. Building a stronger foundation for the future, one tile at a time.
            </p>
          </div>

          {/* Links Column */}
          <div className="flex flex-col sm:flex-row gap-12 text-center md:text-left">
            <div>
              <h4 className="text-gray-900 font-bold mb-4 tracking-tight">Careers Center</h4>
              <ul className="space-y-3 text-sm text-gray-500 font-medium">
                <li><a href="#" className="hover:text-[#D60041] transition-colors">Open Positions</a></li>
                <li><a href="#" className="hover:text-[#D60041] transition-colors">Life at Mariwasa</a></li>
                <li><a href="#" className="hover:text-[#D60041] transition-colors">Internship Programs</a></li>
                <li><a href="#" className="hover:text-[#D60041] transition-colors">Applicant Login</a></li>
              </ul>
            </div>

            {/* Contact Column */}
            <div className="hidden sm:block">
              <h4 className="text-gray-900 font-bold mb-4 tracking-tight">Contact HR</h4>
              <ul className="space-y-3 text-sm text-gray-500 font-medium">
                <li className="flex items-center justify-center md:justify-start gap-3">
                  <Mail className="w-4 h-4 text-gray-400" /> 
                  <span className="hover:text-[#D60041] transition-colors cursor-pointer">careers@mariwasa.com</span>
                </li>
                <li className="flex items-center justify-center md:justify-start gap-3">
                  <Phone className="w-4 h-4 text-gray-400" /> 
                  <span>(02) 8123-4567</span>
                </li>
                <li className="flex items-center justify-center md:justify-start gap-3">
                  <MapPin className="w-4 h-4 text-gray-400" /> 
                  <span>Sto. Tomas, Batangas</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-gray-100 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-gray-400 text-[11px] font-bold tracking-widest uppercase">
            © {new Date().getFullYear()} Mariwasa Siam Ceramics Inc.
          </p>
          <div className="flex gap-6 text-[11px] text-gray-400 font-bold tracking-widest uppercase">
            <a href="#" className="hover:text-[#D60041] transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-[#D60041] transition-colors">Terms of Use</a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
