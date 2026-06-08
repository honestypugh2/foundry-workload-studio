import { useEffect, useMemo, useState } from 'react';

interface Props {
  initial: Record<string, unknown>;
  busy: boolean;
  onSubmit: (payload: unknown) => void;
  onReset?: () => void;
}

/**
 * Minimal JSON editor + reset/submit. Keeps the explorer schema-agnostic so
 * a new use case is automatically supported as long as it provides a
 * `sample_input` from the gateway registry.
 */
export default function RequestEditor({ initial, busy, onSubmit, onReset }: Props) {
  const pretty = useMemo(() => JSON.stringify(initial, null, 2), [initial]);
  const [text, setText] = useState(pretty);
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    setText(pretty);
    setParseError(null);
  }, [pretty]);

  const submit = () => {
    try {
      const parsed = JSON.parse(text);
      setParseError(null);
      onSubmit(parsed);
    } catch (err) {
      setParseError((err as Error).message);
    }
  };

  const reset = () => {
    setText(pretty);
    setParseError(null);
    onReset?.();
  };

  return (
    <div className="editor">
      <div className="editor-toolbar">
        <span className="panel-title">Request</span>
        <div className="editor-actions">
          <button type="button" className="btn ghost" onClick={reset}>
            Reset
          </button>
          <button
            type="button"
            className="btn primary"
            onClick={submit}
            disabled={busy}
          >
            {busy ? 'Running…' : 'Run'}
          </button>
        </div>
      </div>
      <textarea
        className="editor-textarea"
        value={text}
        spellCheck={false}
        onChange={(e) => setText(e.target.value)}
      />
      {parseError && <div className="editor-error">JSON error: {parseError}</div>}
    </div>
  );
}
