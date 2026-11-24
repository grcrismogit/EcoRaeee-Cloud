// Globo 3D de puntos (React Three Fiber + three.js), centrado en Ecuador.
// Los continentes se dibujan con puntos de luz y los arcos animados representan
// rutas de traslado de RAEE: dentro de Ecuador y hacia gestores de la región. Se puede arrastrar.
import { Component, useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { feature } from 'topojson-client'
import tierra110 from 'world-atlas/land-110m.json'

const reducir = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const R = 1

// latitud/longitud -> punto en la esfera
function aVector(lat, lon, radio = R) {
  const phi = ((90 - lat) * Math.PI) / 180
  const theta = ((lon + 180) * Math.PI) / 180
  return new THREE.Vector3(-radio * Math.sin(phi) * Math.cos(theta), radio * Math.cos(phi), radio * Math.sin(phi) * Math.sin(theta))
}

const CIUDADES = {
  Quito: [-0.18, -78.47], Guayaquil: [-2.19, -79.89], Cuenca: [-2.9, -79.0], Loja: [-3.99, -79.2],
  Manta: [-0.95, -80.73], Esmeraldas: [0.97, -79.65],
  Bogota: [4.71, -74.07], Lima: [-12.05, -77.04], Panama: [8.98, -79.52], Santiago: [-33.45, -70.67],
  SaoPaulo: [-23.55, -46.63], Mexico: [19.43, -99.13],
}
const RUTAS = [
  ['Quito', 'Guayaquil'], ['Guayaquil', 'Cuenca'], ['Quito', 'Manta'], ['Loja', 'Guayaquil'], ['Esmeraldas', 'Quito'],
  ['Quito', 'Bogota'], ['Guayaquil', 'Lima'], ['Guayaquil', 'Panama'], ['Lima', 'Santiago'],
  ['Quito', 'SaoPaulo'], ['Panama', 'Mexico'],
]

// Máscara de tierra: se dibujan los continentes (Natural Earth) en un canvas equirectangular
function crearMascara() {
  const W = 720, H = 360
  const c = document.createElement('canvas'); c.width = W; c.height = H
  const ctx = c.getContext('2d')
  ctx.fillStyle = '#fff'
  const tierra = feature(tierra110, tierra110.objects.land)
  const poligonos = tierra.features.flatMap((f) => (f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates))
  for (const poligono of poligonos) {
    ctx.beginPath()
    for (const anillo of poligono) {
      anillo.forEach(([lon, lat], i) => {
        const x = ((lon + 180) / 360) * W, y = ((90 - lat) / 180) * H
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)
      })
      ctx.closePath()
    }
    ctx.fill('evenodd')
  }
  const datos = ctx.getImageData(0, 0, W, H).data
  return (lat, lon) => {
    const x = Math.min(W - 1, Math.floor(((lon + 180) / 360) * W)), y = Math.min(H - 1, Math.floor(((90 - lat) / 180) * H))
    return datos[(y * W + x) * 4] > 128
  }
}

// Textura redonda para que cada punto sea un círculo suave
function texturaPunto() {
  const c = document.createElement('canvas'); c.width = c.height = 64
  const g = c.getContext('2d')
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32)
  grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(0.5, 'rgba(255,255,255,.9)'); grad.addColorStop(1, 'rgba(255,255,255,0)')
  g.fillStyle = grad; g.fillRect(0, 0, 64, 64)
  return new THREE.CanvasTexture(c)
}

function Puntos() {
  const { posiciones, colores } = useMemo(() => {
    const esTierra = crearMascara()
    const N = 24000
    const pos = [], col = []
    const verde = new THREE.Color('#34d399'), menta = new THREE.Color('#a7f3d0')
    const dorado = aVector(-1.5, -78.6) // Ecuador: los puntos cercanos brillan más
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2
      const r = Math.sqrt(1 - y * y)
      const t = Math.PI * (3 - Math.sqrt(5)) * i
      const x = Math.cos(t) * r, z = Math.sin(t) * r
      const lat = (Math.asin(y) * 180) / Math.PI
      // inversa de aVector para obtener la longitud
      const lon = ((Math.atan2(z, -x) * 180) / Math.PI) - 180
      const lonN = ((lon + 540) % 360) - 180
      if (!esTierra(lat, lonN)) continue
      const v = new THREE.Vector3(x, y, z).multiplyScalar(R * 1.002)
      pos.push(v.x, v.y, v.z)
      const cerca = Math.max(0, 1 - v.distanceTo(dorado) / 0.45)
      const c = verde.clone().lerp(menta, cerca)
      col.push(c.r, c.g, c.b)
    }
    return { posiciones: new Float32Array(pos), colores: new Float32Array(col) }
  }, [])
  const mapa = useMemo(texturaPunto, [])
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[posiciones, 3]} />
        <bufferAttribute attach="attributes-color" args={[colores, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.024} map={mapa} vertexColors transparent alphaTest={0.05} depthWrite={false} sizeAttenuation />
    </points>
  )
}

function Atmosfera() {
  const material = useMemo(() => new THREE.ShaderMaterial({
    uniforms: { c: { value: new THREE.Color('#2dd4bf') } },
    vertexShader: 'varying vec3 vN; void main(){ vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: 'uniform vec3 c; varying vec3 vN; void main(){ float i = pow(0.68 - dot(vN, vec3(0.0,0.0,1.0)), 2.6); gl_FragColor = vec4(c, 1.0) * i; }',
    blending: THREE.AdditiveBlending, side: THREE.BackSide, transparent: true, depthWrite: false,
  }), [])
  return <mesh scale={1.16} material={material}><sphereGeometry args={[R, 64, 64]} /></mesh>
}

// Un arco: se dibuja, una "cabeza" de luz lo recorre y se apaga; luego vuelve a empezar
function Arco({ desde, hasta, retraso }) {
  const { curva, geometria, total } = useMemo(() => {
    const a = aVector(...CIUDADES[desde], R * 1.004), b = aVector(...CIUDADES[hasta], R * 1.004)
    const altura = 0.03 + a.distanceTo(b) * 0.45
    const medio = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(R * (1 + altura))
    const curva = new THREE.QuadraticBezierCurve3(a, medio, b)
    const geometria = new THREE.TubeGeometry(curva, 64, 0.0042, 6, false)
    return { curva, geometria, total: geometria.index.count }
  }, [desde, hasta])
  const cabeza = useRef()
  const material = useRef()
  useFrame(({ clock }) => {
    const ciclo = 3.2
    const t = ((clock.elapsedTime + retraso) % ciclo) / ciclo
    const avance = Math.min(1, t / 0.55)
    const n = Math.floor(total * avance / 6) * 6
    geometria.setDrawRange(0, n)
    if (material.current) material.current.opacity = t < 0.75 ? 0.9 : 0.9 * (1 - (t - 0.75) / 0.25)
    if (cabeza.current) {
      cabeza.current.position.copy(curva.getPoint(avance))
      cabeza.current.visible = t < 0.6
    }
  })
  return (
    <group>
      <mesh geometry={geometria}><meshBasicMaterial ref={material} color="#fde68a" transparent opacity={0.9} /></mesh>
      <mesh ref={cabeza}><sphereGeometry args={[0.009, 12, 12]} /><meshBasicMaterial color="#ffffff" /></mesh>
    </group>
  )
}

// Ciudad: punto blanco con un anillo que late
function Ciudad({ lat, lon, retraso }) {
  const anillo = useRef()
  const pos = useMemo(() => aVector(lat, lon, R * 1.004), [lat, lon])
  const giro = useMemo(() => { const o = new THREE.Object3D(); o.position.copy(pos); o.lookAt(pos.clone().multiplyScalar(2)); return o.quaternion.clone() }, [pos])
  useFrame(({ clock }) => {
    const t = ((clock.elapsedTime + retraso) % 2) / 2
    if (anillo.current) { anillo.current.scale.setScalar(1 + t * 2.4); anillo.current.material.opacity = 0.8 * (1 - t) }
  })
  return (
    <group position={pos} quaternion={giro}>
      <mesh><circleGeometry args={[0.008, 16]} /><meshBasicMaterial color="#ffffff" /></mesh>
      <mesh ref={anillo}><ringGeometry args={[0.01, 0.013, 32]} /><meshBasicMaterial color="#fde68a" transparent side={THREE.DoubleSide} /></mesh>
    </group>
  )
}

function Globo({ arrastre }) {
  const ref = useRef()
  // giro base para que Ecuador quede de frente a la cámara
  const base = useMemo(() => { const v = aVector(-1.5, -78.6); return -Math.atan2(v.x, v.z) }, [])
  useFrame((estado, dt) => {
    const g = ref.current
    if (!g) return
    const a = arrastre.current
    if (!a.activo) a.dy *= 0.94 // el arrastre se frena suavemente…
    a.offset += a.dy * dt
    if (!a.activo) a.offset += (0 - a.offset) * 0.008 // …y el globo vuelve a mirar a Ecuador
    const vaiven = reducir() ? 0 : Math.sin(estado.clock.elapsedTime * 0.12) * 0.35
    g.rotation.y = base + vaiven + a.offset
    g.rotation.x += (a.rx - g.rotation.x) * 0.08
    estado.camera.position.x += (estado.pointer.x * 0.25 - estado.camera.position.x) * 0.04
    estado.camera.position.y += (estado.pointer.y * 0.18 - estado.camera.position.y) * 0.04
    estado.camera.lookAt(0, 0, 0)
  })
  return (
    <group ref={ref} rotation={[0.08, base, 0]}>
      <mesh><sphereGeometry args={[R, 64, 64]} /><meshBasicMaterial color="#0b1a2b" /></mesh>
      <Puntos />
      {RUTAS.map(([d, h], i) => <Arco key={`${d}-${h}`} desde={d} hasta={h} retraso={i * 0.45} />)}
      {Object.entries(CIUDADES).map(([nombre, [lat, lon]], i) => <Ciudad key={nombre} lat={lat} lon={lon} retraso={i * 0.3} />)}
    </group>
  )
}

function Escena() {
  const arrastre = useRef({ activo: false, x: 0, y: 0, dy: 0, offset: 0, rx: 0.08 })
  const bajar = (e) => { Object.assign(arrastre.current, { activo: true, x: e.clientX, y: e.clientY }) }
  const mover = (e) => {
    const a = arrastre.current
    if (!a.activo) return
    a.dy = (e.clientX - a.x) * 0.5
    a.rx = Math.max(-0.6, Math.min(0.6, a.rx + (e.clientY - a.y) * 0.004))
    a.x = e.clientX; a.y = e.clientY
  }
  const soltar = () => { arrastre.current.activo = false }
  return (
    <div className="planeta-lienzo" onPointerDown={bajar} onPointerMove={mover} onPointerUp={soltar} onPointerLeave={soltar}
      title="Arrastra para girar el globo">
      <Canvas camera={{ position: [0, 0, 4.1], fov: 40 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}>
        <Globo arrastre={arrastre} />
        <Atmosfera />
      </Canvas>
    </div>
  )
}

class ProtegerWebGL extends Component {
  constructor(p) { super(p); this.state = { error: false } }
  static getDerivedStateFromError() { return { error: true } }
  render() { return this.state.error ? <div className="planeta-respaldo" /> : this.props.children }
}

function hayWebGL() {
  try {
    const c = document.createElement('canvas')
    return Boolean(c.getContext('webgl2') || c.getContext('webgl'))
  } catch { return false }
}

export default function Planeta() {
  if (!hayWebGL()) return <div className="planeta-respaldo" />
  return <ProtegerWebGL><Escena /></ProtegerWebGL>
}
