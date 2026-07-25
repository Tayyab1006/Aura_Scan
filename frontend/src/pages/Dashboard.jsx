import React, { useState, useEffect, useRef } from 'react';
import { Activity, AlertTriangle, Building2, FlaskConical, Globe2, ShieldCheck, Wifi } from 'lucide-react';
import CameraView from '../components/CameraView';
import VitalCard from '../components/VitalCard';
import WaveformGraph from '../components/WaveformGraph';

const enterpriseMetrics = [
  { label: 'Regions Ready', value: '6', detail: 'NA, EU, GCC, APAC, LATAM, Africa' },
  { label: 'Safety Mode', value: 'Fail Closed', detail: 'clinical use disabled by default' },
  { label: 'Operational Mode', value: 'Research', detail: 'not for patient dependency' },
];

const assuranceItems = [
  { icon: ShieldCheck, label: 'Governance', value: 'JWT-secured control plane' },
  { icon: Globe2, label: 'Validation Gap', value: 'requires clinical study before patient use' },
  { icon: FlaskConical, label: 'Prototype Status', value: 'research telemetry only' },
];

const Dashboard = () => {
  const [isActive, setIsActive] = useState(false);
  const [vitals, setVitals] = useState({ bpm: '--', rr: '--', quality: 0, sampleReliability: 0, samplesCollected: 0 });
  const [scanResult, setScanResult] = useState(null);
  const [scanActive, setScanActive] = useState(false);
  const [scanTimeLeft, setScanTimeLeft] = useState(0);
  const [scanProgress, setScanProgress] = useState(0);
  const [signalData, setSignalData] = useState([]);
  const [signalStatus, setSignalStatus] = useState('connecting');
  const [clinicalUseEnabled, setClinicalUseEnabled] = useState(false);
  const [safetyNotice, setSafetyNotice] = useState('Prototype telemetry only. Not for emergency or clinical decisions.');
  const [wsReady, setWsReady] = useState(false);
  const [lastError, setLastError] = useState('');
  const ws = useRef(null);
  const API_BASE = 'https://aura-scan-vnfn.onrender.com';

  useEffect(() => {
    ws.current = new WebSocket(`${API_BASE.replace('http', 'ws')}/ws`);

    ws.current.onopen = () => {
      setSignalStatus('connected');
      setWsReady(true);
      setLastError('');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (typeof data.clinical_use_enabled === 'boolean') {
        setClinicalUseEnabled(data.clinical_use_enabled);
      }
      if (data.safety_notice) {
        setSafetyNotice(data.safety_notice);
      }
      if (data.type === 'vitals') {
        setVitals({
          bpm: Math.round(data.bpm),
          rr: Math.round(data.rr),
          quality: data.quality,
          sampleReliability: data.sample_reliability || 0,
          samplesCollected: data.samples_collected || 0,
        });
        setSignalData(data.signal);
        setScanActive(Boolean(data.scan_active));
        setScanTimeLeft(Number(data.scan_time_left) || 0);
        setScanProgress(Number(data.scan_progress) || 0);
      } else if (data.type === 'scan_result') {
        setScanResult(data);
        setIsActive(false);
        setScanActive(false);
        setScanTimeLeft(0);
        setScanProgress(100);
        if (data.accepted) {
          setVitals({
            bpm: Math.round(data.bpm),
            rr: Math.round(data.rr),
            quality: data.quality,
            sampleReliability: data.sample_reliability || 0,
            samplesCollected: data.samples_collected || 0,
          });
        }
      } else if (data.type === 'error') {
        setLastError(data.message || 'Face not detected');
        setVitals((prev) => ({ ...prev, quality: data.quality, sampleReliability: 0 }));
      }
    };

    ws.current.onerror = () => {
      setSignalStatus('error');
      setLastError('WebSocket connection error');
    };

    ws.current.onclose = () => {
      setSignalStatus('disconnected');
      setWsReady(false);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const sendFrame = (frame) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'frame', image: frame, timestamp: Date.now() }));
    }
  };

  const toggleStream = async () => {
    const newState = !isActive;
    const endpoint = newState ? '/start-stream' : '/stop-stream';

    if (newState) {
      setScanResult(null);
    }

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to toggle stream');
      }

      setIsActive(newState);
    } catch (err) {
      console.error('Failed to toggle stream', err);
      setLastError(err.message);
    }
  };

  const getHealthStatus = (bpm) => {
    if (bpm === '--') return 'stable';
    if (bpm < 60) return 'athletic';
    if (bpm <= 100) return 'stable';
    return 'elevated';
  };

  return (
    <div className="min-h-screen bg-void-900 text-white">
      <header className="border-b border-white/10 bg-void-800/70">
        <div className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-md border border-aura-green/30 bg-aura-green/10 px-3 py-2 text-xs font-semibold uppercase tracking-widest text-aura-green">
              <Building2 size={16} />
              Multinational Health Intelligence
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-white lg:text-5xl">
              AURA <span className="text-aura-green">Global</span>
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-void-400">
              Research telemetry for non-contact vital sign experiments. Not a certified patient monitor, emergency device, or life-support system.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-flow-col sm:auto-cols-max">
            <div className="rounded-lg border border-white/10 bg-void-900 px-4 py-3">
              <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-void-400">
                <Wifi size={14} />
                Network
              </div>
              <p className={`mt-2 text-sm font-semibold uppercase ${wsReady ? 'text-aura-green' : 'text-aura-red'}`}>
                {signalStatus}
              </p>
            </div>
            <button
              onClick={toggleStream}
              disabled={scanActive || !wsReady}
              className={`rounded-lg border px-6 py-3 text-sm font-semibold uppercase tracking-widest transition-all duration-300 ${
                scanActive
                  ? 'cursor-not-allowed border-aura-blue bg-aura-blue/20 text-aura-blue opacity-70'
                  : isActive
                  ? 'border-aura-red bg-aura-red/20 text-aura-red hover:bg-aura-red/30'
                  : 'border-aura-green bg-aura-green/20 text-aura-green hover:bg-aura-green/30'
              }`}
            >
              {scanActive ? 'Scanning...' : isActive ? 'Stop Scan' : 'Start Scan'}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 py-8 xl:grid-cols-4">
        <section className="xl:col-span-4 rounded-lg border border-aura-red/40 bg-aura-red/10 p-5 text-aura-red">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div className="flex gap-3">
              <AlertTriangle className="mt-1 shrink-0" size={22} />
              <div>
                <p className="text-sm font-semibold uppercase tracking-widest">Safety Critical Warning</p>
                <p className="mt-2 max-w-4xl text-sm leading-6 text-red-100">
                  {safetyNotice} If someone may be in danger, use an approved medical device and contact emergency services immediately.
                </p>
              </div>
            </div>
            <div className="rounded-md border border-aura-red/40 px-3 py-2 text-xs font-semibold uppercase tracking-widest">
              Clinical Use: {clinicalUseEnabled ? 'Enabled' : 'Disabled'}
            </div>
          </div>
        </section>

        <section className="grid gap-4 xl:col-span-4 md:grid-cols-3">
          {enterpriseMetrics.map((metric) => (
            <div key={metric.label} className="rounded-lg border border-white/10 bg-void-800 p-5">
              <p className="text-xs font-semibold uppercase tracking-widest text-void-400">{metric.label}</p>
              <p className="mt-3 text-3xl font-bold text-white">{metric.value}</p>
              <p className="mt-2 text-sm text-void-400">{metric.detail}</p>
            </div>
          ))}
        </section>

        <div className="space-y-6 xl:col-span-3">
          <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
            <div className="h-[520px]">
              <CameraView isActive={isActive} onFrame={sendFrame} />
            </div>

            <div className="grid gap-4">
              {assuranceItems.map(({ icon: Icon, label, value }) => (
                <div key={label} className="rounded-lg border border-white/10 bg-void-800 p-5">
                  <div className="flex items-center gap-3 text-aura-green">
                    <Icon size={20} />
                    <p className="text-xs font-semibold uppercase tracking-widest">{label}</p>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-void-300">{value}</p>
                </div>
              ))}
            </div>
          </div>

          <WaveformGraph data={signalData} />

          {!wsReady && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-amber-100">
              Backend connection is offline. Start the API on port 8001 before scanning.
            </div>
          )}

          {lastError && (
            <div className="rounded-lg border border-amber-500/40 bg-void-800 p-4 text-amber-200">
              <p className="mb-2 text-xs font-semibold uppercase tracking-widest">Attention</p>
              <p className="text-sm">{lastError}</p>
            </div>
          )}

          {scanActive && (
            <div className="rounded-lg border border-aura-blue/20 bg-aura-blue/5 p-4 text-aura-blue">
              <p className="text-xs font-semibold uppercase tracking-widest">Enterprise Scan In Progress</p>
              <p className="mt-2 text-sm">Maintain position while the signal quality engine checks whether the sample is usable for research telemetry.</p>
              <div className="mt-4 flex items-end justify-between">
                <p className="text-3xl font-bold">{scanTimeLeft}s</p>
                <p className="text-sm text-void-300">{scanProgress}% complete</p>
              </div>
            </div>
          )}
        </div>

        <aside className="space-y-6">
          <VitalCard
            label="Heart Rate"
            value={vitals.bpm}
            unit="BPM"
            colorClass="text-aura-green"
            status={getHealthStatus(vitals.bpm)}
          />
          <VitalCard
            label="Respiration"
            value={vitals.rr}
            unit="BRPM"
            colorClass="text-aura-blue"
            status="stable"
          />

          <div className="rounded-lg border border-white/10 bg-void-800 p-6">
            <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-void-400">Signal Quality</p>
            <div className="h-2 w-full overflow-hidden rounded-full bg-void-700">
              <div
                className="h-full bg-aura-green transition-all duration-500"
                style={{ width: `${vitals.quality}%` }}
              ></div>
            </div>
            <div className="flex justify-between mt-2">
              <span className="text-void-500 text-xs font-mono">0%</span>
              <span className="text-void-500 text-xs font-mono">{vitals.quality}%</span>
            </div>
            {scanActive && (
              <div className="mt-4 text-xs text-void-400 uppercase tracking-widest">
                Progress: {scanProgress}%
              </div>
            )}
          </div>

          <div className="rounded-lg border border-white/10 bg-void-800 p-6">
            <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-void-400">Safety Gate</p>
            <div className="grid gap-4">
              <div>
                <div className="flex justify-between text-xs text-void-400">
                  <span>Sample Reliability</span>
                  <span>{vitals.sampleReliability}%</span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-void-700">
                  <div className="h-full bg-aura-blue transition-all duration-500" style={{ width: `${vitals.sampleReliability}%` }}></div>
                </div>
              </div>
              <div className="flex justify-between text-sm text-void-300">
                <span>Samples Collected</span>
                <span className="font-semibold text-white">{vitals.samplesCollected}</span>
              </div>
              <p className="text-xs leading-5 text-void-500">
                The app rejects weak scans and never replaces approved emergency or clinical monitoring equipment.
              </p>
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-void-800 p-6">
            <div className="mb-3 flex items-center gap-2 text-void-400">
              <Activity size={16} />
              <p className="text-xs font-semibold uppercase tracking-widest">Signal Interpretation</p>
            </div>
            <div className="text-2xl font-bold uppercase text-white">{vitals.bpm === '--' ? 'Awaiting' : 'Telemetry Only'}</div>
            <p className="mt-3 text-xs leading-5 text-void-500">
              No diagnosis, triage, treatment, or emergency decision should be made from this screen.
            </p>
          </div>

          {scanResult && (
            <div className={`rounded-lg border p-6 ${scanResult.accepted ? 'border-aura-blue/20 bg-aura-blue/5 text-aura-blue' : 'border-aura-red/30 bg-aura-red/10 text-aura-red'}`}>
              <p className="mb-3 text-xs font-semibold uppercase tracking-widest">Final Scan Result</p>
              <div className="grid gap-3">
                <div className="flex justify-between text-sm">
                  <span>Result</span>
                  <span className="font-semibold">{scanResult.accepted ? 'Research sample accepted' : 'Rejected'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Clinical Use</span>
                  <span className="font-semibold">{scanResult.clinical_use_enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Heart Rate</span>
                  <span className="font-semibold">{scanResult.bpm || '--'} BPM</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Respiration</span>
                  <span className="font-semibold">{scanResult.rr || '--'} BRPM</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Quality</span>
                  <span className="font-semibold">{scanResult.quality}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Reliability</span>
                  <span className="font-semibold">{scanResult.sample_reliability || 0}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Usable Signal</span>
                  <span className="font-semibold">{scanResult.collected_seconds || 0}s</span>
                </div>
                <p className="mt-3 text-xs text-void-300">{scanResult.message}</p>
                <p className="text-xs leading-5 text-void-400">{scanResult.safety_notice}</p>
              </div>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
};

export default Dashboard;
