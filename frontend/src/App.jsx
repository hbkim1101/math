import { useCallback, useEffect, useState } from 'react'

const SCENE_TYPES = [
  { id: 'equation', label: '수식' },
  { id: 'graph', label: '그래프' },
  { id: 'text', label: '텍스트' },
  { id: 'steps', label: '단계' },
]

const EFFECTS = [
  { id: 'write', label: '등장 (Write)' },
  { id: 'fade_in', label: '페이드인' },
  { id: 'draw', label: '그리기 (Draw)' },
  { id: 'indicate', label: '강조' },
]

const DEFAULT_SCENES = {
  equation: { type: 'equation', latex: 'y = x^2', effect: 'write', wait: 2 },
  graph: {
    type: 'graph',
    function: 'x**2',
    x_range: [-3, 3],
    y_range: [-1, 9],
    color: 'BLUE',
    effect: 'draw',
    wait: 3,
  },
  text: { type: 'text', content: '설명 텍스트', effect: 'fade_in', wait: 2 },
  steps: {
    type: 'steps',
    items: ['x^2 - 5x + 6 = 0', '(x-2)(x-3) = 0', 'x = 2, 3'],
    effect: 'write',
    wait: 3,
  },
}

function sceneSummary(scene) {
  switch (scene.type) {
    case 'equation':
      return scene.latex || '수식'
    case 'graph':
      return scene.function || '그래프'
    case 'text':
      return scene.content || '텍스트'
    case 'steps':
      return `${scene.items?.length || 0}단계`
    default:
      return scene.type
  }
}

function SceneEditor({ scene, onChange }) {
  const update = (key, value) => onChange({ ...scene, [key]: value })

  return (
    <div className="props">
      <div className="field">
        <label>효과</label>
        <select value={scene.effect} onChange={(e) => update('effect', e.target.value)}>
          {EFFECTS.map((e) => (
            <option key={e.id} value={e.id}>{e.label}</option>
          ))}
        </select>
      </div>

      <div className="field">
        <label>대기 시간 (초)</label>
        <input
          type="number"
          min={0}
          max={30}
          step={0.5}
          value={scene.wait}
          onChange={(e) => update('wait', parseFloat(e.target.value) || 0)}
        />
      </div>

      {scene.type === 'equation' && (
        <div className="field">
          <label>LaTeX 수식</label>
          <input
            value={scene.latex || ''}
            onChange={(e) => update('latex', e.target.value)}
            placeholder="y = x^2 - 4x + 3"
          />
        </div>
      )}

      {scene.type === 'graph' && (
        <>
          <div className="field">
            <label>함수 (Python syntax)</label>
            <input
              value={scene.function || ''}
              onChange={(e) => update('function', e.target.value)}
              placeholder="x**2 - 4*x + 3"
            />
          </div>
          <div className="field">
            <label>X 범위 (min, max)</label>
            <input
              value={(scene.x_range || []).join(', ')}
              onChange={(e) => {
                const parts = e.target.value.split(',').map((s) => parseFloat(s.trim()))
                if (parts.length === 2 && parts.every((n) => !Number.isNaN(n))) {
                  update('x_range', parts)
                }
              }}
              placeholder="-1, 5"
            />
          </div>
          <div className="field">
            <label>Y 범위 (min, max)</label>
            <input
              value={(scene.y_range || []).join(', ')}
              onChange={(e) => {
                const parts = e.target.value.split(',').map((s) => parseFloat(s.trim()))
                if (parts.length === 2 && parts.every((n) => !Number.isNaN(n))) {
                  update('y_range', parts)
                }
              }}
              placeholder="-2, 6"
            />
          </div>
          <div className="field">
            <label>강조</label>
            <select
              value={scene.highlight || ''}
              onChange={(e) => update('highlight', e.target.value || null)}
            >
              <option value="">없음</option>
              <option value="vertex">꼭짓점</option>
            </select>
          </div>
        </>
      )}

      {scene.type === 'text' && (
        <div className="field">
          <label>텍스트</label>
          <input
            value={scene.content || ''}
            onChange={(e) => update('content', e.target.value)}
            placeholder="꼭짓점 (2, -1)"
          />
        </div>
      )}

      {scene.type === 'steps' && (
        <div className="field">
          <label>단계 (한 줄에 하나)</label>
          <textarea
            rows={5}
            value={(scene.items || []).join('\n')}
            onChange={(e) => update('items', e.target.value.split('\n').filter(Boolean))}
            placeholder={'x^2 - 5x + 6 = 0\n(x-2)(x-3) = 0\nx = 2, 3'}
          />
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [title, setTitle] = useState('이차함수 그래프')
  const [scenes, setScenes] = useState([])
  const [selected, setSelected] = useState(0)
  const [quality, setQuality] = useState('low')
  const [rendering, setRendering] = useState(false)
  const [status, setStatus] = useState('')
  const [statusType, setStatusType] = useState('')
  const [videoUrl, setVideoUrl] = useState(null)

  useEffect(() => {
    fetch('/api/template')
      .then((r) => r.json())
      .then((data) => {
        setTitle(data.title)
        setScenes(data.scenes)
      })
      .catch(() => {
        setScenes([
          DEFAULT_SCENES.equation,
          DEFAULT_SCENES.graph,
          DEFAULT_SCENES.text,
        ])
      })
  }, [])

  const updateScene = useCallback((index, updated) => {
    setScenes((prev) => prev.map((s, i) => (i === index ? updated : s)))
  }, [])

  const addScene = (type) => {
    const newScene = { ...DEFAULT_SCENES[type] }
    setScenes((prev) => [...prev, newScene])
    setSelected(scenes.length)
  }

  const removeScene = (index) => {
    setScenes((prev) => prev.filter((_, i) => i !== index))
    setSelected((s) => Math.max(0, Math.min(s, scenes.length - 2)))
  }

  const moveScene = (index, dir) => {
    const next = index + dir
    if (next < 0 || next >= scenes.length) return
    setScenes((prev) => {
      const copy = [...prev]
      ;[copy[index], copy[next]] = [copy[next], copy[index]]
      return copy
    })
    setSelected(next)
  }

  const handleRender = async () => {
    setRendering(true)
    setStatus('Manim 렌더링 중... (첫 실행은 1~2분 걸릴 수 있습니다)')
    setStatusType('')
    setVideoUrl(null)

    try {
      const res = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project: { title, scenes },
          quality,
        }),
      })

      const data = await res.json()
      if (!res.ok) {
        const detail = typeof data.detail === 'object'
          ? JSON.stringify(data.detail, null, 2)
          : data.detail
        throw new Error(detail || 'Render failed')
      }

      setVideoUrl(data.video_url)
      setStatus('렌더 완료! 아래에서 미리보기하거나 다운로드하세요.')
      setStatusType('success')
    } catch (err) {
      setStatus(`오류: ${err.message}`)
      setStatusType('error')
    } finally {
      setRendering(false)
    }
  }

  const current = scenes[selected]

  return (
    <div className="app">
      <header className="header">
        <h1><span>Math</span> Studio</h1>
        <div className="header-actions">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ width: 200 }}
            placeholder="영상 제목"
          />
          <select
            className="quality-select"
            value={quality}
            onChange={(e) => setQuality(e.target.value)}
          >
            <option value="low">480p (빠름)</option>
            <option value="medium">720p</option>
            <option value="high">1080p</option>
          </select>
          <button
            className="btn-primary"
            onClick={handleRender}
            disabled={rendering || scenes.length === 0}
          >
            {rendering && <span className="spinner" />}
            {rendering ? '렌더링...' : '미리보기 렌더'}
          </button>
          {videoUrl && (
            <a href={videoUrl} download className="btn-secondary" style={{ textDecoration: 'none' }}>
              MP4 다운로드
            </a>
          )}
        </div>
      </header>

      <div className="main">
        <aside className="panel">
          <div className="panel-title">장면</div>
          <ul className="scene-list">
            {scenes.map((scene, i) => (
              <li
                key={i}
                className={`scene-item ${selected === i ? 'active' : ''}`}
                onClick={() => setSelected(i)}
              >
                <span className="scene-badge">{i + 1}</span>
                <span className="scene-label">{sceneSummary(scene)}</span>
              </li>
            ))}
          </ul>
          <div className="type-grid" style={{ padding: '0 0.75rem' }}>
            {SCENE_TYPES.map((t) => (
              <button key={t.id} className="type-btn" onClick={() => addScene(t.id)}>
                + {t.label}
              </button>
            ))}
          </div>
        </aside>

        <section className="preview">
          <div className="preview-area">
            {videoUrl ? (
              <video src={videoUrl} controls autoPlay key={videoUrl} />
            ) : (
              <div className="preview-placeholder">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                <p>장면을 추가하고 <strong>미리보기 렌더</strong>를 누르면 Manim 애니메이션이 여기에 표시됩니다.</p>
              </div>
            )}
          </div>
          <div className={`preview-status ${statusType}`}>{status}</div>

          <div className="timeline">
            <div className="timeline-bar">
              {scenes.map((scene, i) => (
                <div
                  key={i}
                  className={`timeline-block ${selected === i ? 'active' : ''}`}
                  onClick={() => setSelected(i)}
                >
                  {i + 1}. {scene.type}
                  <span>{scene.wait}s</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <aside className="panel">
          <div className="panel-title">속성</div>
          {current ? (
            <>
              <div className="type-grid" style={{ padding: '0 1rem' }}>
                {SCENE_TYPES.map((t) => (
                  <button
                    key={t.id}
                    className={`type-btn ${current.type === t.id ? 'active' : ''}`}
                    onClick={() => updateScene(selected, { ...DEFAULT_SCENES[t.id], wait: current.wait, effect: current.effect })}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <SceneEditor scene={current} onChange={(s) => updateScene(selected, s)} />
              <div style={{ padding: '0 1rem 1rem', display: 'flex', gap: '0.5rem' }}>
                <button className="btn-secondary" style={{ flex: 1 }} onClick={() => moveScene(selected, -1)} disabled={selected === 0}>
                  ↑ 위로
                </button>
                <button className="btn-secondary" style={{ flex: 1 }} onClick={() => moveScene(selected, 1)} disabled={selected === scenes.length - 1}>
                  ↓ 아래로
                </button>
                <button className="btn-danger" onClick={() => removeScene(selected)}>
                  삭제
                </button>
              </div>
            </>
          ) : (
            <p style={{ padding: '1rem', color: 'var(--muted)', fontSize: '0.85rem' }}>
              왼쪽에서 장면을 추가하세요.
            </p>
          )}
        </aside>
      </div>
    </div>
  )
}
