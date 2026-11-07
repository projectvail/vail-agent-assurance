// VAIL Assurance panel: one page showing what the VAIL Agent Assurance Engine knows about each Hermes
// profile. Loaded uncompiled by Hermes Desktop, so no JSX: jsx()/jsxs() from react/jsx-runtime.
import {
  Badge,
  Button,
  Codicon,
  EmptyState,
  ErrorState,
  Loader,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  StatusDot,
  host,
  profileColor
} from '@hermes/plugin-sdk'
import { useCallback, useEffect, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const PATH = '/vail-assurance'
const SEVERITY_VARIANT = { critical: 'destructive', high: 'destructive', medium: 'warn', low: 'muted' }
const STAGE_LABEL = {
  created: 'Created',
  source_ready: 'Source uploaded',
  context_ready: 'Context ready',
  behaviors_ready: 'Risks found',
  probes_ready: 'Probes ready'
}

function age(iso) {
  if (!iso) return ''
  const seconds = Math.max(0, (Date.now() - Date.parse(iso)) / 1000)
  if (seconds < 90) return 'just now'
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`
  if (seconds < 86400) return `${Math.round(seconds / 3600)} hr ago`
  return `${Math.round(seconds / 86400)} d ago`
}

function hostOf(url) {
  try {
    return new URL(url).host
  } catch {
    return url || ''
  }
}

// -- small pieces ---------------------------------------------------------------------------------

function Muted({ children, className = '' }) {
  return jsx('span', { className: `text-(--ui-text-tertiary) ${className}`, children })
}

function profileStatus(profile) {
  const vail = profile.vail
  if (!profile.link) return { tone: 'muted', label: 'Not linked to VAIL' }
  if (!vail || vail.error) return { tone: 'bad', label: vail?.error || 'Unavailable' }
  if (vail.active_operation) return { tone: 'warn', label: `${vail.active_operation}…` }
  if (vail.outdated || profile.changed_since_scan) return { tone: 'warn', label: 'Changed since last scan' }
  if (vail.risks && (vail.risks.critical || vail.risks.high)) return { tone: 'bad', label: STAGE_LABEL[vail.stage] || vail.stage }
  return { tone: 'good', label: STAGE_LABEL[vail.stage] || vail.stage }
}

function RiskBadges({ vail }) {
  if (!vail || !vail.risks) return null
  const items = ['critical', 'high', 'medium', 'low']
    .filter(severity => vail.risks[severity])
    .map(severity =>
      jsx(Badge, { variant: SEVERITY_VARIANT[severity], children: `${vail.risks[severity]} ${severity}` }, severity)
    )
  if (!items.length) {
    return jsx(Badge, { variant: 'success', children: vail.stage === 'probes_ready' || vail.stage === 'behaviors_ready' ? 'No risks' : '—' })
  }
  return jsx('div', { className: 'flex flex-wrap items-center gap-1', children: items })
}

function RiskList({ ctx, agentId }) {
  const [state, setState] = useState({ loading: true })
  useEffect(() => {
    let live = true
    ctx
      .rest(`/agents/${encodeURIComponent(agentId)}/risks`)
      .then(data => live && setState({ risks: data.risks }))
      .catch(error => live && setState({ error: String(error?.message || error) }))
    return () => {
      live = false
    }
  }, [ctx, agentId])

  if (state.loading) return jsx('div', { className: 'py-3', children: jsx(Loader, {}) })
  if (state.error) return jsx(Muted, { className: 'block py-2 text-xs', children: state.error })
  if (!state.risks.length) return jsx(Muted, { className: 'block py-2 text-xs', children: 'VAIL found no behavior risks.' })

  return jsx('div', {
    className: 'mt-2 flex flex-col divide-y divide-(--ui-stroke-secondary) border-t border-(--ui-stroke-secondary)',
    children: state.risks.map(risk =>
      jsxs(
        'div',
        {
          className: 'flex flex-col gap-1 py-2',
          children: [
            jsxs('div', {
              className: 'flex items-start gap-2',
              children: [
                jsx(Badge, { variant: SEVERITY_VARIANT[risk.severity] || 'muted', children: risk.severity }),
                jsx('span', { className: 'text-xs font-medium text-(--ui-text-primary)', children: risk.title })
              ]
            }),
            risk.description && jsx(Muted, { className: 'text-xs leading-5', children: risk.description }),
            jsxs('div', {
              className: 'flex flex-wrap items-center gap-1 text-[0.6875rem]',
              children: [
                ...risk.tools.map(tool => jsx(Badge, { variant: 'outline', size: 'xs', children: tool }, tool)),
                risk.probes.length
                  ? jsx(Muted, { children: `${risk.probes.length} probe${risk.probes.length > 1 ? 's' : ''}` })
                  : jsx(Badge, { variant: 'warn', size: 'xs', children: 'no probe' })
              ]
            })
          ]
        },
        risk.id
      )
    )
  })
}

function LinkControl({ profile, agents, onLink }) {
  const hermesAgents = agents.filter(agent => agent.platform === 'hermes')
  const others = agents.filter(agent => agent.platform !== 'hermes')
  const [choice, setChoice] = useState(profile.suggested || '')
  const options = [...hermesAgents, ...others]
  if (!options.length) return jsx(Muted, { className: 'text-xs', children: 'No agents on VAIL yet' })
  return jsxs('div', {
    className: 'flex items-center gap-1.5',
    children: [
      jsxs(Select, {
        value: choice || undefined,
        onValueChange: setChoice,
        children: [
          jsx(SelectTrigger, { className: 'h-7 w-56 text-xs', children: jsx(SelectValue, { placeholder: 'Choose a VAIL agent' }) }),
          jsx(SelectContent, {
            children: options.map(agent =>
              jsx(
                SelectItem,
                { value: agent.agent_id, children: `${agent.name} · ${agent.platform}` },
                agent.agent_id
              )
            )
          })
        ]
      }),
      jsx(Button, { size: 'xs', disabled: !choice, onClick: () => onLink(profile.name, choice), children: 'Link' })
    ]
  })
}

function ProfileRow({ ctx, profile, agents, onLink }) {
  const [open, setOpen] = useState(false)
  const status = profileStatus(profile)
  const vail = profile.vail
  const parts = [profile.has_soul ? 'SOUL' : 'no SOUL', `${profile.skills} skill${profile.skills === 1 ? '' : 's'}`]
  if (profile.plugins.length) parts.push(profile.plugins.join(', '))
  const ready = vail && !vail.error && vail.risk_total > 0

  return jsxs('div', {
    className: 'rounded-[4px] border border-(--ui-stroke-secondary) px-3 py-2.5',
    children: [
      jsxs('div', {
        className: 'flex flex-wrap items-center gap-x-4 gap-y-2',
        children: [
          jsxs('div', {
            className: 'flex min-w-48 flex-1 items-center gap-2',
            children: [
              jsx('span', {
                className: 'inline-block size-2.5 shrink-0 rounded-full border border-(--ui-stroke-secondary)',
                style: { background: profileColor(profile.name) || 'var(--ui-text-quaternary)' }
              }),
              jsxs('div', {
                className: 'flex flex-col',
                children: [
                  jsx('span', { className: 'text-sm font-medium text-(--ui-text-primary)', children: profile.name }),
                  jsx(Muted, { className: 'text-[0.6875rem]', children: parts.join(' · ') })
                ]
              })
            ]
          }),
          jsxs('div', {
            className: 'flex min-w-44 items-center gap-1.5 text-xs',
            children: [jsx(StatusDot, { tone: status.tone }), jsx('span', { className: 'text-(--ui-text-secondary)', children: status.label })]
          }),
          vail && !vail.error
            ? jsxs('div', {
                className: 'flex min-w-56 flex-col gap-1',
                children: [
                  jsx(RiskBadges, { vail }),
                  jsx(Muted, {
                    className: 'text-[0.6875rem]',
                    children: [
                      `${vail.probes} probe${vail.probes === 1 ? '' : 's'}`,
                      vail.untested ? ` · ${vail.untested} risk${vail.untested === 1 ? '' : 's'} untested` : '',
                      vail.scanned_at ? ` · scanned ${age(vail.scanned_at)}` : ''
                    ].join('')
                  })
                ]
              })
            : null,
          jsxs('div', {
            className: 'ml-auto flex items-center gap-1',
            children: profile.link
              ? [
                  ready &&
                    jsx(
                      Button,
                      {
                        size: 'xs',
                        variant: 'outline',
                        onClick: () => setOpen(value => !value),
                        children: [jsx(Codicon, { name: open ? 'chevron-up' : 'chevron-down' }), open ? 'Hide risks' : 'View risks']
                      },
                      'toggle'
                    ),
                  jsx(Button, { size: 'xs', variant: 'ghost', onClick: () => onLink(profile.name, null), children: 'Unlink' }, 'unlink')
                ]
              : [jsx(LinkControl, { profile, agents, onLink }, 'link')]
          })
        ]
      }),
      open && profile.link ? jsx(RiskList, { ctx, agentId: profile.link }) : null
    ]
  })
}

// -- the page -------------------------------------------------------------------------------------

function AssurancePage({ ctx }) {
  const [state, setState] = useState({ loading: true })

  const load = useCallback(
    (refresh = false) => {
      setState(previous => ({ ...previous, loading: true }))
      return ctx
        .rest(`/fleet${refresh ? '?refresh=1' : ''}`, { timeoutMs: 120000 })
        .then(view => setState({ view }))
        .catch(error => setState({ error: String(error?.message || error) }))
    },
    [ctx]
  )

  useEffect(() => {
    load(false)
  }, [load])

  const onLink = useCallback(
    (profile, agentId) =>
      ctx
        .rest('/link', { method: 'POST', body: { profile, agent_id: agentId } })
        .then(() => load(false))
        .catch(error => host.notify({ kind: 'error', message: `Could not update the link: ${error?.message || error}` })),
    [ctx, load]
  )

  const view = state.view
  const profiles = view?.profiles || []
  const linked = profiles.filter(p => p.vail && !p.vail.error)
  const highRisks = linked.reduce((sum, p) => sum + (p.vail.risks?.critical || 0) + (p.vail.risks?.high || 0), 0)
  const changed = profiles.filter(p => p.changed_since_scan).length

  let body
  if (state.error) {
    body = jsx(ErrorState, { title: 'The assurance panel could not load', description: state.error })
  } else if (!view) {
    body = jsx('div', { className: 'flex justify-center py-10', children: jsx(Loader, {}) })
  } else if (!view.vail.connected) {
    body = jsx(ErrorState, {
      title: 'Not connected to VAIL',
      description: `${view.vail.error || 'Unknown error'}. Set your VAIL access token (VAIL_TOKEN) in Settings → Plugins → vail-assurance-panel, or with hermes config set VAIL_TOKEN.`
    })
  } else if (!profiles.length) {
    body = jsx(EmptyState, { title: 'No Hermes profiles found' })
  } else {
    body = jsx('div', {
      className: 'flex flex-col gap-2',
      children: profiles.map(profile => jsx(ProfileRow, { ctx, profile, agents: view.agents, onLink }, profile.name))
    })
  }

  return jsx('div', {
    className: 'h-full overflow-y-auto',
    children: jsxs('div', {
      className: 'mx-auto flex max-w-5xl flex-col gap-4 px-6 py-5',
      children: [
        jsxs('div', {
          className: 'flex items-start justify-between gap-4',
          children: [
            jsxs('div', {
              className: 'flex flex-col gap-0.5',
              children: [
                jsxs('div', {
                  className: 'flex items-center gap-2 text-base font-medium text-(--ui-text-primary)',
                  children: [jsx(Codicon, { name: 'shield' }), 'Agent assurance']
                }),
                jsx(Muted, {
                  className: 'text-xs',
                  children: view?.vail?.connected
                    ? `VAIL Agent Assurance Engine · ${view.vail.organization || 'organization'} · ${hostOf(view.vail.url)}`
                    : 'VAIL Agent Assurance Engine'
                })
              ]
            }),
            jsx(Button, {
              size: 'sm',
              variant: 'outline',
              disabled: state.loading,
              onClick: () => load(true),
              children: [jsx(Codicon, { name: 'refresh' }), state.loading ? 'Refreshing…' : 'Refresh']
            })
          ]
        }),
        view?.vail?.connected
          ? jsx('div', {
              className: 'flex flex-wrap gap-x-5 gap-y-1 text-xs text-(--ui-text-secondary)',
              children: [
                `${profiles.length} profile${profiles.length === 1 ? '' : 's'}`,
                `${linked.length} on VAIL`,
                `${highRisks} high-severity risk${highRisks === 1 ? '' : 's'}`,
                `${changed} changed since scan`
              ].map(text => jsx('span', { children: text }, text))
            })
          : null,
        body
      ]
    })
  })
}

export default {
  id: 'vail-assurance-panel',
  name: 'VAIL Agent Assurance',
  register(ctx) {
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: PATH }, render: () => jsx(AssurancePage, { ctx }) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: PATH, label: 'Assurance', codicon: 'shield' } }
    ])
  }
}
