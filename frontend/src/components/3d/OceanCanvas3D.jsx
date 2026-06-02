import { Canvas, useFrame } from '@react-three/fiber';
import { memo, useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

function OceanCanvas3D() {
  return (
    <Canvas
      camera={{ position: [0, 8, 20], fov: 55 }}
      gl={{ antialias: true, alpha: true }}
      style={{ position: 'fixed', top: 0, left: 0, zIndex: 0, pointerEvents: 'none' }}
    >
      <fog attach="fog" args={['#020C18', 18, 60]} />
      <OceanPlane />
      <RouteArcs />
      <FloatingVessel />
      <AtmosphericParticles />
      <ambientLight intensity={0.15} />
      <pointLight position={[10, 8, -20]} color="#00C8E0" intensity={0.8} />
      <pointLight position={[-15, 5, -30]} color="#0044AA" intensity={0.5} />
    </Canvas>
  );
}

function OceanPlane() {
  const materialRef = useRef();
  const shaderRef = useRef(null);

  const segments = useMemo(() => {
    if (typeof window === 'undefined') return 64;
    const cores = window.navigator.hardwareConcurrency || 8;
    const isMobile = window.innerWidth < 768;
    if (cores < 4 || isMobile) return 16;
    return 64;
  }, []);

  const geometry = useMemo(() => new THREE.PlaneGeometry(120, 120, segments, segments), [segments]);

  useEffect(() => {
    geometry.rotateX(-Math.PI / 2);
    return () => geometry.dispose();
  }, [geometry]);

  useEffect(() => {
    if (!materialRef.current) return;
    materialRef.current.onBeforeCompile = (shader) => {
      shader.uniforms.uTime = { value: 0 };
      shader.vertexShader = `uniform float uTime; varying float vElevation;\n${shader.vertexShader}`;
      shader.vertexShader = shader.vertexShader.replace(
        '#include <begin_vertex>',
        [
          'vec3 transformed = position;',
          'float wave1 = sin(position.x * 0.3 + uTime * 0.8) * 0.3;',
          'float wave2 = cos(position.z * 0.4 + uTime * 0.6) * 0.2;',
          'transformed.y += wave1 + wave2;',
          'vElevation = transformed.y;',
        ].join('\n')
      );
      shader.fragmentShader = `varying float vElevation;\n${shader.fragmentShader}`;
      shader.fragmentShader = shader.fragmentShader.replace(
        'vec4 diffuseColor = vec4( diffuse, opacity );',
        [
          'float crest = smoothstep(0.1, 0.45, vElevation);',
          'vec3 crestColor = vec3(0.0, 0.78, 0.88);',
          'vec4 diffuseColor = vec4(diffuse + crestColor * crest * 0.08, opacity);',
        ].join('\n')
      );
      shaderRef.current = shader;
    };
    materialRef.current.needsUpdate = true;
  }, []);

  useFrame(({ clock }) => {
    if (document.visibilityState !== 'visible') return;
    if (shaderRef.current) {
      shaderRef.current.uniforms.uTime.value = clock.getElapsedTime();
    }
  });

  return (
    <mesh geometry={geometry} position={[0, -3, -15]}>
      <meshStandardMaterial
        ref={materialRef}
        color="#020F1E"
        emissive="#001828"
        emissiveIntensity={0.4}
        metalness={0.1}
        roughness={0.85}
      />
    </mesh>
  );
}

function RouteArcs() {
  const groupRef = useRef();

  const arcs = useMemo(
    () => [
      {
        id: 'arc1',
        color: '#00C8E0',
        opacity: 0.7,
        points: [
          new THREE.Vector3(-10, 0, 12),
          new THREE.Vector3(-4, 5, 2),
          new THREE.Vector3(6, 4, -4),
          new THREE.Vector3(12, 0, -12),
        ],
      },
      {
        id: 'arc2',
        color: '#00C8E0',
        opacity: 0.7,
        points: [
          new THREE.Vector3(-12, 0, 6),
          new THREE.Vector3(-6, 4, -2),
          new THREE.Vector3(2, 5, -6),
          new THREE.Vector3(10, 1, -10),
        ],
      },
      {
        id: 'arc3',
        color: '#00C8E0',
        opacity: 0.7,
        points: [
          new THREE.Vector3(-8, 0, 10),
          new THREE.Vector3(-2, 3, 0),
          new THREE.Vector3(4, 4, -2),
          new THREE.Vector3(10, 0, -8),
        ],
      },
      {
        id: 'arc4',
        color: '#FF8C00',
        opacity: 0.9,
        pulse: true,
        points: [
          new THREE.Vector3(-6, 0, 8),
          new THREE.Vector3(-1, 4, -1),
          new THREE.Vector3(5, 5, -5),
          new THREE.Vector3(11, 0, -11),
        ],
      },
      {
        id: 'arc5',
        color: '#00C8E0',
        opacity: 0.7,
        points: [
          new THREE.Vector3(-9, 0, 14),
          new THREE.Vector3(-2, 3, 6),
          new THREE.Vector3(4, 4, 2),
          new THREE.Vector3(9, 0, -2),
        ],
      },
    ],
    []
  );

  useFrame(({ clock }) => {
    if (document.visibilityState !== 'visible') return;
    if (groupRef.current) {
      const scale = 0.98 + Math.sin(clock.getElapsedTime() * 0.6) * 0.02;
      groupRef.current.scale.set(scale, scale, scale);
    }
  });

  return (
    <group ref={groupRef} position={[0, 0, -5]}>
      {arcs.map((arc) => (
        <ArcTube key={arc.id} {...arc} />
      ))}
    </group>
  );
}

function ArcTube({ points, color, opacity, pulse }) {
  const materialRef = useRef();
  const geometry = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(points);
    return new THREE.TubeGeometry(curve, 80, 0.025, 6, false);
  }, [points]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame(({ clock }) => {
    if (document.visibilityState !== 'visible') return;
    if (!materialRef.current) return;
    materialRef.current.uniforms.uTime.value = clock.getElapsedTime();
    if (pulse) {
      const pulseValue = 0.4 + Math.abs(Math.sin(clock.getElapsedTime() * 2.1)) * 0.5;
      materialRef.current.uniforms.uOpacity.value = pulseValue;
    }
  });

  const shader = useMemo(
    () => ({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: new THREE.Color(color) },
        uOpacity: { value: opacity },
      },
      vertexShader: `
        varying float vProgress;
        void main() {
          vProgress = uv.x;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uColor;
        uniform float uOpacity;
        varying float vProgress;
        void main() {
          float dashSpeed = fract(vProgress - uTime * 0.4);
          float dash = step(0.5, dashSpeed);
          gl_FragColor = vec4(uColor, dash * uOpacity);
        }
      `,
    }),
    [color, opacity]
  );

  return (
    <mesh geometry={geometry}>
      <shaderMaterial ref={materialRef} args={[shader]} />
    </mesh>
  );
}

function FloatingVessel() {
  const groupRef = useRef();
  const wakeRef = useRef();

  const wakeGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(20 * 3);
    for (let i = 0; i < 20; i += 1) {
      positions[i * 3] = -1.5 - Math.random() * 1.2;
      positions[i * 3 + 1] = -0.2 + Math.random() * 0.2;
      positions[i * 3 + 2] = 0.2 + Math.random() * 0.8;
    }
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geometry;
  }, []);

  useEffect(() => () => wakeGeometry.dispose(), [wakeGeometry]);

  useFrame(({ clock }) => {
    if (document.visibilityState !== 'visible') return;
    if (groupRef.current) {
      const time = clock.getElapsedTime();
      groupRef.current.position.y = -2.5 + Math.sin(time * 0.6) * 0.08;
      groupRef.current.position.x = -6 + ((time * 0.2) % 12);
    }

    if (wakeRef.current) {
      const positions = wakeRef.current.geometry.attributes.position.array;
      for (let i = 0; i < positions.length; i += 3) {
        positions[i] -= 0.01;
        positions[i + 1] += 0.005;
        if (positions[i] < -3) positions[i] = 0.5;
        if (positions[i + 1] > 0.4) positions[i + 1] = -0.2;
      }
      wakeRef.current.geometry.attributes.position.needsUpdate = true;
    }
  });

  return (
    <group ref={groupRef} position={[-6, -2.5, -5]} scale={0.4}>
      <mesh>
        <boxGeometry args={[3.5, 0.6, 1.0]} />
        <meshStandardMaterial color="#0D1F2D" metalness={0.3} roughness={0.7} />
      </mesh>
      <mesh position={[1.2, 0.65, -0.1]}>
        <boxGeometry args={[0.5, 0.7, 0.5]} />
        <meshStandardMaterial color="#102738" metalness={0.2} roughness={0.6} />
      </mesh>
      <mesh position={[-0.6, 0.45, 0]}>
        <boxGeometry args={[0.7, 0.35, 0.4]} />
        <meshStandardMaterial color="#C0392B" />
      </mesh>
      <mesh position={[0.2, 0.45, 0]}>
        <boxGeometry args={[0.7, 0.35, 0.4]} />
        <meshStandardMaterial color="#2980B9" />
      </mesh>
      <mesh position={[1.0, 0.45, 0]}>
        <boxGeometry args={[0.7, 0.35, 0.4]} />
        <meshStandardMaterial color="#27AE60" />
      </mesh>
      <mesh position={[1.45, 0.85, 0.2]}>
        <cylinderGeometry args={[0.1, 0.12, 0.4, 12]} />
        <meshStandardMaterial color="#0B1A26" />
      </mesh>
      <pointLight position={[-1.4, 0.3, 0.6]} color="#00FF66" intensity={0.3} distance={2} />
      <pointLight position={[-1.4, 0.3, -0.6]} color="#FF3D3D" intensity={0.3} distance={2} />
      <points ref={wakeRef} geometry={wakeGeometry}>
        <pointsMaterial color="#00C8E0" size={0.08} transparent opacity={0.35} />
      </points>
    </group>
  );
}

function AtmosphericParticles() {
  const pointsRef = useRef();

  const geometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(600 * 3);
    for (let i = 0; i < 600; i += 1) {
      positions[i * 3] = (Math.random() - 0.5) * 60;
      positions[i * 3 + 1] = Math.random() * 20;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 60;
    }
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geometry;
  }, []);

  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame(() => {
    if (document.visibilityState !== 'visible') return;
    if (!pointsRef.current) return;
    const positions = pointsRef.current.geometry.attributes.position.array;
    for (let i = 0; i < positions.length; i += 3) {
      positions[i + 1] += 0.01;
      if (positions[i + 1] > 20) positions[i + 1] = 0;
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={pointsRef} geometry={geometry}>
      <pointsMaterial color="#00C8E0" size={0.04} transparent opacity={0.25} />
    </points>
  );
}

export default memo(OceanCanvas3D);
