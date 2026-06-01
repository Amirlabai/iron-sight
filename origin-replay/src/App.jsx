import { useCallback, useEffect, useState } from 'react';
import { Play } from 'lucide-react';
import EventPicker from './components/EventPicker';
import StepNavigator from './components/StepNavigator';
import StepDetail from './components/StepDetail';
import ReplayMap from './components/ReplayMap';
import { fetchHistory, fetchOriginReplay, fetchHealth } from './api/replayService';
import { API_PROXY_TARGET, TACTICAL_API_URL } from './utils/constants';
import './App.css';

export default function App() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [search, setSearch] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [replayData, setReplayData] = useState(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [allowStrategic, setAllowStrategic] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setLoadError(null);
      try {
        await fetchHealth();
        const list = await fetchHistory('missiles');
        setEvents(list);
      } catch (err) {
        setLoadError(
          `Cannot reach API at ${TACTICAL_API_URL} (proxy → ${API_PROXY_TARGET}). ` +
          `Start backend on :8080, then restart Vite. ${err.message}`,
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const loadReplay = useCallback(async (event) => {
    if (!event?.id) return;
    setReplayLoading(true);
    setReplayData(null);
    setStepIndex(0);
    try {
      const data = await fetchOriginReplay({
        id: event.id,
        category: 'missiles',
        allowStrategic,
      });
      setReplayData(data);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setReplayLoading(false);
    }
  }, [allowStrategic]);

  const handleSelectEvent = (ev) => {
    setSelectedEvent(ev);
    setLoadError(null);
    loadReplay(ev);
  };

  useEffect(() => {
    if (selectedEvent) loadReplay(selectedEvent);
  }, [allowStrategic]); // eslint-disable-line react-hooks/exhaustive-deps

  const steps = replayData?.replay?.steps || [];
  const currentStep = steps[stepIndex] || null;
  const replayOrigin = replayData?.replay?.final?.origin;
  const storedOrigin = replayData?.stored_origin;
  const originMatch = storedOrigin != null && replayOrigin === storedOrigin;

  useEffect(() => {
    const onKey = (e) => {
      if (!steps.length) return;
      if (e.key === 'ArrowLeft') setStepIndex((i) => Math.max(0, i - 1));
      if (e.key === 'ArrowRight') setStepIndex((i) => Math.min(steps.length - 1, i + 1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [steps.length]);

  return (
    <div className="origin-replay-app">
      <header className="app-header">
        <h1>
          Origin Replay
          <span>Iron Sight Dev</span>
        </h1>
        <label className="strategic-toggle">
          <input
            type="checkbox"
            checked={allowStrategic}
            onChange={(e) => setAllowStrategic(e.target.checked)}
          />
          allow_strategic
        </label>
        {selectedEvent && (
          <span className="selected-label">
            Event #{selectedEvent.id}
            {replayLoading && ' — computing…'}
          </span>
        )}
      </header>

      {loadError && (
        <div className="error-banner">{loadError}</div>
      )}

      <div className="app-body">
        <EventPicker
          events={events}
          selectedId={selectedEvent?.id}
          onSelect={handleSelectEvent}
          loading={loading}
          search={search}
          onSearchChange={setSearch}
        />

        <main className="main-panel">
          <ReplayMap step={currentStep} />
          <div className="bottom-panel">
            <StepDetail
              step={currentStep}
              storedOrigin={storedOrigin}
              replayOrigin={replayOrigin}
              match={originMatch}
            />
            <StepNavigator
              steps={steps}
              currentIndex={stepIndex}
              onIndexChange={setStepIndex}
            />
          </div>
        </main>
      </div>

      {!selectedEvent && !loading && (
        <div className="empty-hint">
          <Play size={20} />
          <p>Select a missile archive event to step through origin determination.</p>
        </div>
      )}
    </div>
  );
}
