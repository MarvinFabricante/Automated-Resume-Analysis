import React, { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  Settings2, 
  Cpu, 
  FileText, 
  Save, 
  RotateCcw,
  Sliders,
  AlertTriangle,
  Plus
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { 
  useGetMatchingConfigQuery,
  useUpdateMatchingWeightsMutation,
  useUpdateMatchingThresholdsMutation,
  useGetFormTemplatesQuery,
  useCreateFormTemplateMutation,
  useDeleteFormTemplateMutation
} from '../../redux/api/apiSlice';


const MatchingTab = () => {
  const { data: config, isLoading } = useGetMatchingConfigQuery();
  const [updateWeights] = useUpdateMatchingWeightsMutation();
  const [updateThresholds] = useUpdateMatchingThresholdsMutation();
  
  const [weights, setWeights] = useState({
    skills_weight: 0.45,
    experience_weight: 0.25,
    education_weight: 0.15,
    certifications_weight: 0.10,
    location_weight: 0.05
  });

  const [thresholds, setThresholds] = useState({
    fuzzy_match_threshold: 0.75,
    minimum_match_score: 30.0,
    ai_score_weight: 0.8,
    rule_score_weight: 0.2,
    transferable_skills_cap: 2
  });

  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (config) {
      setWeights(config.weights);
      setThresholds(config.thresholds);
    }
  }, [config]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateWeights(weights).unwrap();
      await updateThresholds(thresholds).unwrap();
      alert("Configuration saved successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to save configuration.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleWeightChange = (key, value) => {
    setWeights(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  const handleThresholdChange = (key, value) => {
    setThresholds(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  if (isLoading) return <div className="p-10 text-center text-gray-400">Loading configuration...</div>;

  const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-8 animate-in fade-in">
      
      {Math.abs(totalWeight - 1.0) > 0.01 && (
        <div className="bg-amber-50 border border-amber-200 text-amber-700 px-4 py-3 rounded-xl flex items-start gap-3">
          <AlertTriangle size={20} className="shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-sm">Warning: Weights must sum to 1.0</h4>
            <p className="text-xs mt-1">Current sum is {totalWeight.toFixed(2)}. This may cause inaccurate overall matching percentages.</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
            <Sliders className="text-[#D10043]" size={20} /> Base Algorithm Weights
          </h3>
          
          <div className="space-y-5">
            {[
              { key: 'skills_weight', label: 'Skills & Keywords' },
              { key: 'experience_weight', label: 'Experience Relevance' },
              { key: 'education_weight', label: 'Education & Degree' },
              { key: 'certifications_weight', label: 'Certifications' },
              { key: 'location_weight', label: 'Location Match' },
            ].map(item => (
              <div key={item.key}>
                <div className="flex justify-between mb-1.5 text-xs font-bold text-gray-700">
                  <span>{item.label}</span>
                  <span>{Math.round(weights[item.key] * 100)}%</span>
                </div>
                <input 
                  type="range" 
                  min="0" max="1" step="0.01" 
                  value={weights[item.key]}
                  onChange={(e) => handleWeightChange(item.key, e.target.value)}
                  className="w-full accent-[#D10043]"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
            <Cpu className="text-[#D10043]" size={20} /> AI & Thresholds
          </h3>
          
          <div className="space-y-6">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-2">AI Score Dominance (0 to 1)</label>
              <div className="flex items-center gap-4">
                <input 
                  type="range" 
                  min="0" max="1" step="0.05" 
                  value={thresholds.ai_score_weight}
                  onChange={(e) => handleThresholdChange('ai_score_weight', e.target.value)}
                  className="w-full accent-[#D10043]"
                />
                <span className="text-sm font-bold w-12 text-right">{Math.round(thresholds.ai_score_weight * 100)}%</span>
              </div>
              <p className="text-[10px] text-gray-400 mt-1">Weight given to LLM reasoning vs deterministic rule engine.</p>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 mb-2">Fuzzy Match Threshold (0 to 1)</label>
              <input 
                type="number" 
                min="0" max="1" step="0.05" 
                value={thresholds.fuzzy_match_threshold}
                onChange={(e) => handleThresholdChange('fuzzy_match_threshold', e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-[#D10043]"
              />
            </div>
            
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-2">Minimum Global Match Score (%)</label>
              <input 
                type="number" 
                min="0" max="100" 
                value={thresholds.minimum_match_score}
                onChange={(e) => handleThresholdChange('minimum_match_score', e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:border-[#D10043]"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
        <button 
          onClick={() => { setWeights(config.weights); setThresholds(config.thresholds); }}
          className="px-5 py-2.5 rounded-xl border border-gray-200 text-gray-600 font-bold text-xs hover:bg-gray-50 flex items-center gap-2 transition-all"
        >
          <RotateCcw size={14} /> Discard Changes
        </button>
        <button 
          onClick={handleSave}
          disabled={isSaving}
          className="bg-[#D10043] text-white px-6 py-2.5 rounded-xl font-bold text-xs hover:bg-[#b00038] flex items-center gap-2 transition-all disabled:opacity-70 shadow-lg shadow-red-100"
        >
          <Save size={14} /> {isSaving ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </div>
  );
};


const TemplatesTab = () => {
  const { data: templates = [], isLoading } = useGetFormTemplatesQuery();
  const [deleteTemplate] = useDeleteFormTemplateMutation();

  const handleDelete = async (id) => {
    if(window.confirm("Are you sure you want to delete this template?")) {
      await deleteTemplate(id);
    }
  };

  if (isLoading) return <div className="p-10 text-center text-gray-400">Loading templates...</div>;

  return (
    <div className="animate-in fade-in space-y-6">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Application Forms</h3>
          <p className="text-xs text-gray-400">Manage custom fields required for candidates applying to jobs.</p>
        </div>
        <button className="bg-gray-900 text-white px-5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 hover:bg-gray-800 transition-all">
          <Plus size={14} /> Create Template
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {templates.map(t => (
          <div key={t.id} className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col">
            <div className="flex justify-between items-start mb-3">
              <h4 className="font-bold text-gray-900">{t.name}</h4>
              {t.is_default && <span className="bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded text-[10px] font-bold">DEFAULT</span>}
            </div>
            <p className="text-xs text-gray-500 mb-4 flex-1 line-clamp-2">{t.description}</p>
            
            <div className="bg-gray-50 rounded-xl p-3 mb-4">
              <p className="text-[10px] font-bold text-gray-400 uppercase mb-2">Fields ({t.fields?.length || 0})</p>
              <div className="flex flex-wrap gap-1.5">
                {t.fields?.slice(0, 3).map((f, i) => (
                  <span key={i} className="bg-white border border-gray-200 px-2 py-1 rounded text-[10px] text-gray-600">
                    {f.field_name}
                  </span>
                ))}
                {(t.fields?.length || 0) > 3 && <span className="text-xs text-gray-400">+{t.fields.length - 3} more</span>}
              </div>
            </div>

            <div className="flex gap-2">
              <button className="flex-1 border border-gray-200 text-gray-600 rounded-lg py-1.5 text-xs font-bold hover:bg-gray-50 transition-colors">Edit</button>
              <button 
                onClick={() => handleDelete(t.id)}
                className="flex-1 bg-red-50 text-red-600 rounded-lg py-1.5 text-xs font-bold hover:bg-red-100 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        ))}

        {templates.length === 0 && (
          <div className="col-span-full py-12 text-center bg-gray-50 border border-dashed border-gray-200 rounded-2xl">
             <FileText className="mx-auto text-gray-300 mb-3" size={32} />
             <h4 className="font-bold text-gray-900">No Templates Found</h4>
             <p className="text-sm text-gray-500 mt-1">Create your first form template to customize job applications.</p>
          </div>
        )}
      </div>
    </div>
  );
};


const SystemSettings = () => {
  const [activeTab, setActiveTab] = useState('matching');

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
      <Helmet>
        <title>Admin Page - System Settings</title>
      </Helmet>
      
      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 max-w-[1400px] mx-auto px-10 py-10">
        
        <div className="mb-10">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 flex items-center gap-3">
            <Settings2 className="text-[#D10043]" size={28} /> System Settings
          </h2>
          <p className="text-sm text-gray-400 font-medium tracking-wide mt-1">
            Global configurations, algorithm parameters, and templates.
          </p>
        </div>

        <div className="mb-8 border-b border-gray-100">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('matching')}
              className={`pb-4 text-sm font-bold transition-all relative ${activeTab === 'matching' ? 'text-[#D10043]' : 'text-gray-400 hover:text-gray-600'}`}
            >
              Matching Algorithm
              {activeTab === 'matching' && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-[#D10043] rounded-t-full"></div>}
            </button>
            <button
              onClick={() => setActiveTab('templates')}
              className={`pb-4 text-sm font-bold transition-all relative ${activeTab === 'templates' ? 'text-[#D10043]' : 'text-gray-400 hover:text-gray-600'}`}
            >
              Form Templates
              {activeTab === 'templates' && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-[#D10043] rounded-t-full"></div>}
            </button>
          </div>
        </div>

        <div className="min-h-[400px]">
          {activeTab === 'matching' && <MatchingTab />}
          {activeTab === 'templates' && <TemplatesTab />}
        </div>

        </main>
      </div>
    </div>
  );
};

export default SystemSettings;
