import React from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const WaveformGraph = ({ data }) => {
  const chartData = {
    labels: data.map((_, i) => i),
    datasets: [
      {
        label: 'Enterprise rPPG Signal',
        data: data,
        borderColor: '#00ff9f',
        borderWidth: 2,
        tension: 0.4,
        pointRadius: 0,
        fill: true,
        backgroundColor: 'rgba(0, 255, 159, 0.1)',
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: { display: false },
      y: {
        display: true,
        grid: { color: 'rgba(255,255,255,0.05)' },
        ticks: { display: false }
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false },
    },
  };

  return (
    <div className="h-64 w-full overflow-hidden rounded-lg border border-white/10 bg-void-800 p-4">
      <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-void-400">Real-time Enterprise Waveform</p>
      <div className="h-48">
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
};

export default WaveformGraph;
