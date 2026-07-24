import React from 'react';

const VitalCard = ({ label, value, unit, colorClass, status }) => {
  return (
    <div className="group rounded-lg border border-white/10 bg-void-800 p-6 transition-all duration-500 hover:border-aura-green/50">
      <div className="flex justify-between items-start mb-4">
        <p className="text-xs font-semibold uppercase tracking-widest text-void-400">{label}</p>
        <div className={`w-2 h-2 rounded-full ${status === 'stable' ? 'bg-aura-green' : 'bg-aura-red'} animate-pulse`}></div>
      </div>
      <div className={`text-6xl font-mono font-bold ${colorClass} transition-all duration-300 group-hover:scale-105`}>
        {value === '--' ? '--' : value}
        <span className="text-xl ml-2 text-void-500 font-normal">{unit}</span>
      </div>
    </div>
  );
};

export default VitalCard;
