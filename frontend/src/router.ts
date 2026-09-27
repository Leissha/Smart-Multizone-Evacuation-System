import { createRouter, createWebHistory } from 'vue-router'
import OverviewView from './views/OverviewView.vue'
import NodesView from './views/NodesView.vue'
import MonitorView from './views/MonitorView.vue'
import ControlView from './views/ControlView.vue'
import AutomationView from './views/AutomationView.vue'

export default createRouter({ history: createWebHistory(), routes: [
  { path: '/', component: OverviewView },
  { path: '/nodes', component: NodesView },
  { path: '/monitor', component: MonitorView },
  { path: '/control', component: ControlView },
  { path: '/automation', component: AutomationView },
  { path: '/devices', redirect: '/nodes' }, { path: '/management', redirect: '/nodes' },
  { path: '/live-data', redirect: '/monitor' }, { path: '/alarms', redirect: '/monitor?tab=alarms' },
  { path: '/rules', redirect: '/automation' },
] })
