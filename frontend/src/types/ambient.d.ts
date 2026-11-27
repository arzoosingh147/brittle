// Global ambient definitions for React, JSX, and dependencies

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
  interface Element extends any {}
  interface ElementClass extends any {}
}

declare namespace React {
  type FC<P = {}> = (props: P) => any;
  type ReactNode = any;
  type Element = any;
  interface HTMLAttributes<T = any> {
    [key: string]: any;
  }
  interface ButtonHTMLAttributes<T = any> extends HTMLAttributes<T> {
    [key: string]: any;
  }
  function useState<T>(init: T | (() => T)): [T, (val: T | ((prev: T) => T)) => void];
  function useState<T = undefined>(): [T | undefined, (val: T | ((prev: T) => T)) => void];
  function useEffect(effect: () => void | (() => void), deps?: any[]): void;
  function useMemo<T>(factory: () => T, deps?: any[]): T;
  function useCallback<T extends (...args: any[]) => any>(callback: T, deps?: any[]): T;
  function forwardRef<T, P = {}>(render: (props: P, ref: any) => any): any;
}

declare module "react" {
  export = React;
  export as namespace React;
}

declare module "react/jsx-runtime" {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare module "lucide-react" {
  export const GitBranch: any;
  export const Lock: any;
  export const Globe: any;
  export const RefreshCw: any;
  export const Settings2: any;
  export const ExternalLink: any;
  export const X: any;
  export const Save: any;
  export const AlertCircle: any;
  export const Loader2: any;
  export const CheckCircle2: any;
  export const Clock: any;
  export const ShieldCheck: any;
  export const GitPullRequest: any;
  export const Terminal: any;
  export const Sparkles: any;
  export const Database: any;
  export const LayoutDashboard: any;
  export const ArrowRight: any;
  export const ShieldAlert: any;
  export const Zap: any;
  export const CheckCircle: any;
  export const BarChart3: any;
  export const AlertTriangle: any;
  export const Shield: any;
  export const Code2: any;
  export const FileCode: any;
  export const User: any;
  export const AlertOctagon: any;
  export const ArrowLeft: any;
  export const Filter: any;
  export const Plus: any;
  export const FolderGit2: any;
  export const PlusCircle: any;
  export const Trash2: any;
  export const Check: any;
  export const Sliders: any;
  export const RotateCcw: any;
  const icons: { [key: string]: any };
  export default icons;
}

declare module "clsx" {
  export function clsx(...args: any[]): string;
  export default clsx;
}

declare module "tailwind-merge" {
  export function twMerge(...args: any[]): string;
}

declare module "next/navigation" {
  export function useParams(): Record<string, string | string[]>;
  export function useRouter(): {
    push(url: string): void;
    back(): void;
    forward(): void;
    refresh(): void;
    replace(url: string): void;
  };
  export function redirect(url: string): never;
}

declare module "next/link" {
  const Link: (props: any) => any;
  export default Link;
}

declare module "next-auth" {
  export default function NextAuth(config: any): any;
}

declare module "next-auth/providers/github" {
  export default function GitHub(options: any): any;
}
