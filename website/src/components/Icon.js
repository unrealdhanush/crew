// Icons for <Card icon="..."> and friends, by lucide name in kebab-case (https://lucide.dev/icons).
// Only the icons listed here are bundled; add an import and a map entry to use another one.
import React from 'react';
import {
  Activity, Bell, Book, BookOpen, Bot, Box, Building2, Calendar, Check, ChevronDown, Cloud, Copy, Code, Compass, Container, Cpu, Database,
  Download, ExternalLink, FileText, Folder, Gauge, GitBranch, Globe, KeyRound, Layers, LifeBuoy, Lightbulb, Link, ListChecks, Lock,
  Map, MessageSquare, Mic, Network, Nfc, Package, Play, Plug, Printer, Puzzle, Radar, Rocket, Scan, Search, Send,
  Server, Settings, Shield, ShieldCheck, Smartphone, Sparkles, Star, Tag, Target, Terminal, Ticket, Upload, Users,
  Wand2, Waypoints, Workflow, Wrench, Zap,
} from 'lucide-react';

const ICONS = {
  activity: Activity, bell: Bell, book: Book, 'book-open': BookOpen, bot: Bot, box: Box, building: Building2,
  calendar: Calendar, check: Check, 'chevron-down': ChevronDown, cloud: Cloud, copy: Copy, code: Code, compass: Compass, container: Container, cpu: Cpu, database: Database,
  download: Download, 'external-link': ExternalLink, 'file-text': FileText, folder: Folder, gauge: Gauge, 'git-branch': GitBranch, globe: Globe,
  key: KeyRound, layers: Layers, 'life-buoy': LifeBuoy, lightbulb: Lightbulb, link: Link, 'list-checks': ListChecks,
  lock: Lock, map: Map, message: MessageSquare, mic: Mic, network: Network, nfc: Nfc, package: Package, play: Play,
  plug: Plug, printer: Printer, puzzle: Puzzle, radar: Radar, rocket: Rocket, scan: Scan, search: Search, send: Send,
  server: Server, settings: Settings, shield: Shield, 'shield-check': ShieldCheck, smartphone: Smartphone,
  sparkles: Sparkles, star: Star, tag: Tag, target: Target, terminal: Terminal, ticket: Ticket, upload: Upload,
  users: Users, wand: Wand2, waypoints: Waypoints, workflow: Workflow, wrench: Wrench, zap: Zap,
};

export default function Icon({name, size = 18, ...props}) {
  const Svg = ICONS[name];
  if (!Svg) {
    throw new Error(`Unknown icon "${name}". Add it to src/components/Icon.js`);  // fail the build, not silently
  }
  return <Svg size={size} strokeWidth={1.75} aria-hidden="true" {...props} />;
}
