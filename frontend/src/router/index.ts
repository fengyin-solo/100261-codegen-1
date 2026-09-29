import { createRouter, createWebHistory } from 'vue-router'

import Dashboard from '@/views/Dashboard.vue'
const Flightstand = () => import('@/views/flightstand/index.vue')
const Marshalling = () => import('@/views/marshalling/index.vue')
const Bridge = () => import('@/views/bridge/index.vue')
const Baggage = () => import('@/views/baggage/index.vue')
const Catering = () => import('@/views/catering/index.vue')
const Fueling = () => import('@/views/fueling/index.vue')
const Deicing = () => import('@/views/deicing/index.vue')
const Lavatory = () => import('@/views/lavatory/index.vue')
const Pushback = () => import('@/views/pushback/index.vue')
const Gse = () => import('@/views/gse/index.vue')
const Cargo = () => import('@/views/cargo/index.vue')
const Clearance = () => import('@/views/clearance/index.vue')
const Turnaround = () => import('@/views/turnaround/index.vue')
const Ramp = () => import('@/views/ramp/index.vue')
const Weather2 = () => import('@/views/weather2/index.vue')
const Vehicle = () => import('@/views/vehicle/index.vue')
const Staffshift = () => import('@/views/staffshift/index.vue')
const Runway = () => import('@/views/runway/index.vue')
const Emergencyplan = () => import('@/views/emergencyplan/index.vue')
const Qualitycheck = () => import('@/views/qualitycheck/index.vue')
const Shuttlebus = () => import('@/views/shuttlebus/index.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: Dashboard },
    { path: '/flightstand', name: 'flightstand', component: Flightstand },
    { path: '/marshalling', name: 'marshalling', component: Marshalling },
    { path: '/bridge', name: 'bridge', component: Bridge },
    { path: '/baggage', name: 'baggage', component: Baggage },
    { path: '/catering', name: 'catering', component: Catering },
    { path: '/fueling', name: 'fueling', component: Fueling },
    { path: '/deicing', name: 'deicing', component: Deicing },
    { path: '/lavatory', name: 'lavatory', component: Lavatory },
    { path: '/pushback', name: 'pushback', component: Pushback },
    { path: '/gse', name: 'gse', component: Gse },
    { path: '/cargo', name: 'cargo', component: Cargo },
    { path: '/clearance', name: 'clearance', component: Clearance },
    { path: '/turnaround', name: 'turnaround', component: Turnaround },
    { path: '/ramp', name: 'ramp', component: Ramp },
    { path: '/weather2', name: 'weather2', component: Weather2 },
    { path: '/vehicle', name: 'vehicle', component: Vehicle },
    { path: '/staffshift', name: 'staffshift', component: Staffshift },
    { path: '/runway', name: 'runway', component: Runway },
    { path: '/emergencyplan', name: 'emergencyplan', component: Emergencyplan },
    { path: '/qualitycheck', name: 'qualitycheck', component: Qualitycheck },
    { path: '/shuttlebus', name: 'shuttlebus', component: Shuttlebus },
  ],
})

export default router
