import { useEffect } from 'react'
import { wsClient } from '../../lib/wsClient'
import { useVisionStore } from '../../stores/visionStore'
import './CameraView.css'

const MJPEG_URL = '/api/vision/camera/mjpeg'

export function CameraView() {
  const detections = useVisionStore((s) => s.detections)
  const frameWidth = useVisionStore((s) => s.frameWidth)
  const frameHeight = useVisionStore((s) => s.frameHeight)

  useEffect(() => {
    wsClient.send('camera_subscribe')
    fetch('/api/vision/camera/start', { method: 'POST' }).catch(console.error)

    return () => {
      wsClient.send('camera_unsubscribe')
    }
  }, [])

  return (
    <div className="camera-view">
      <div className="camera-feed-wrap">
        <img src={MJPEG_URL} alt="Live camera" className="camera-feed" />
        {frameWidth > 0 && (
          <svg
            className="detection-overlay"
            viewBox={`0 0 ${frameWidth} ${frameHeight}`}
            preserveAspectRatio="none"
          >
            {detections.map((d, i) => (
              <g key={i}>
                <rect
                  x={d.x * frameWidth}
                  y={d.y * frameHeight}
                  width={d.w * frameWidth}
                  height={d.h * frameHeight}
                  className="bbox"
                />
                <text
                  x={d.x * frameWidth}
                  y={d.y * frameHeight - 4}
                  className="bbox-label"
                >
                  {d.class_name} {(d.confidence * 100).toFixed(0)}%
                </text>
              </g>
            ))}
          </svg>
        )}
      </div>
      <div className="detection-list">
        <h3>Detections</h3>
        {detections.length === 0 ? (
          <p className="muted">No objects detected</p>
        ) : (
          <ul>
            {detections.map((d, i) => (
              <li key={i}>
                {d.class_name} <span className="conf">{(d.confidence * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
