import { useCallback, useEffect, useState } from 'react';
import { Play } from 'lucide-react';
import ReplayMap from '../components/replay/ReplayMap';
import StepDetail from '../components/replay/StepDetail';
import StepNavigator from '../components/replay/StepNavigator';
import { fetchOriginReplay } from '../api/apiService';
import '../components/replay/replay.css';

export default function OriginReplayView({ selectedEvent, active }) {
  const [replayData, setReplayData] = useState(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayError, setReplayError] = useState(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [allowStrategic, setAllowStrategic] = useState(true);

  const loadReplay = useCallback(async (event) => {
    if (!event?.id || event.category !== 'missiles') {
      setReplayData(null);
      return;
    }
    setReplayLoading(true);
    setReplayError(null);
    setReplayData(null);
    setStepIndex(0);
    try {
      const data = await fetchOriginReplay({
        id: event.id,
        category: event.category,
        allowStrategic,
      });
      setReplayData(data);
    } catch (err) {
      setReplayError(err.message || String(err));
    } finally {
      setReplayLoading(false);
    }
  }, [allowStrategic]);

  useEffect(() => {
    if (active && selectedEvent) {
      loadReplay(selectedEvent);
    }
  }, [active, selectedEvent?.id, allowStrategic, loadReplay]);

  const steps = replayData?.replay?.steps || [];
  const currentStep = steps[stepIndex] || null;
  const replayOrigin = replayData?.replay?.final?.origin;
  const storedOrigin = replayData?.stored_origin;
  const originMatch = storedOrigin != null && replayOrigin === storedOrigin;

  useEffect(() => {
    const onKey = (e) => {
      if (!active || !steps.length) return;
      if (e.key === 'ArrowLeft') setStepIndex((i) => Math.max(0, i - 1));
      if (e.key === 'ArrowRight') setStepIndex((i) => Math.min(steps.length - 1, i + 1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [active, steps.length]);

  if (!selectedEvent) {
    return (
      <div className="replay-tool replay-empty">
        <Play size={20} />
        <p>Select a missile event from the sidebar to step through origin determination.</p>
      </div>
    );
  }

  if (selectedEvent.category !== 'missiles') {
    return (
      <div className="replay-tool replay-empty">
        <p>Pipeline replay is available for missile events only.</p>
      </div>
    );
  }

  return (
    <div className="replay-tool">
      <div className="replay-toolbar">
        <label className="strategic-toggle">
          <input
            type="checkbox"
            checked={allowStrategic}
            onChange={(e) => setAllowStrategic(e.target.checked)}
          />
          allow_strategic
        </label>
        <span className="replay-status">
          Event #{selectedEvent.id}
          {replayLoading && ' — computing…'}
        </span>
      </div>

      {replayError && (
        <div className="replay-error">{replayError}</div>
      )}

      <div className="replay-main">
        <ReplayMap step={currentStep} />
        <div className="replay-bottom-panel">
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
      </div>
    </div>
  );
}
