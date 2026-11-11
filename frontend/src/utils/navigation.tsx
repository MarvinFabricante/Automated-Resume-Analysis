'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  forwardRef,
} from 'react';
import {
  useRouter as useNextRouter,
  usePathname as useNextPathname,
  useParams as useNextParams,
} from 'next/navigation';
import NextLink, { LinkProps as NextLinkProps } from 'next/link';

interface NavigationStateContextType {
  getPathState: (path: string) => any;
  setPathState: (path: string, state: any) => void;
}

const NavigationStateContext = createContext<NavigationStateContextType>({
  getPathState: () => null,
  setPathState: () => {},
});

const normalizePath = (path: string): string => {
  if (!path) return '/';
  const clean = path.split('?')[0].split('#')[0];
  if (clean.length > 1 && clean.endsWith('/')) {
    return clean.slice(0, -1);
  }
  return clean;
};

const getStoredStateForPath = (path: string): any => {
  if (typeof window === 'undefined') return null;
  const clean = normalizePath(path);
  try {
    const stored = sessionStorage.getItem(`__nav_state_${clean}`);
    if (stored) {
      return JSON.parse(stored);
    }
    if (window.location.pathname && normalizePath(window.location.pathname) === clean) {
      if (window.history.state && window.history.state.usr) {
        return window.history.state.usr;
      }
    }
  } catch {
    // ignore
  }
  return null;
};

export const NavigationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = useNextPathname() || '/';
  const [statesByPath, setStatesByPath] = useState<Record<string, any>>(() => {
    if (typeof window !== 'undefined') {
      const initialPath = normalizePath(window.location.pathname || '/');
      const initial = getStoredStateForPath(initialPath);
      return initial !== null ? { [initialPath]: initial } : {};
    }
    return {};
  });

  // Restore navigation state from sessionStorage or history on pathname change
  useEffect(() => {
    if (typeof window !== 'undefined' && pathname) {
      const clean = normalizePath(pathname);
      const stored = getStoredStateForPath(clean);
      if (stored !== null) {
        setStatesByPath((prev) => {
          if (prev[clean] === undefined) {
            return { ...prev, [clean]: stored };
          }
          return prev;
        });
      }
    }
  }, [pathname]);

  const setPathState = useCallback((path: string, newState: any) => {
    const clean = normalizePath(path);
    setStatesByPath((prev) => ({ ...prev, [clean]: newState }));
  }, []);

  const getPathState = useCallback(
    (path: string) => {
      const clean = normalizePath(path);
      if (statesByPath[clean] !== undefined) {
        return statesByPath[clean];
      }
      return getStoredStateForPath(clean);
    },
    [statesByPath]
  );

  return (
    <NavigationStateContext.Provider value={{ getPathState, setPathState }}>
      {children}
    </NavigationStateContext.Provider>
  );
};

export interface NavigateOptions {
  state?: any;
  replace?: boolean;
}

export function useNavigate() {
  const router = useNextRouter();
  const { setPathState } = useContext(NavigationStateContext);

  return useCallback(
    (to: string | number, options?: NavigateOptions) => {
      if (typeof to === 'number') {
        if (typeof window !== 'undefined') {
          window.history.go(to);
        }
        return;
      }

      if (options?.state !== undefined) {
        const cleanPath = normalizePath(to);
        setPathState(cleanPath, options.state);
        if (typeof window !== 'undefined') {
          try {
            sessionStorage.setItem(`__nav_state_${cleanPath}`, JSON.stringify(options.state));
          } catch {
            // ignore
          }
        }
      }

      if (options?.replace) {
        router.replace(to);
      } else {
        router.push(to);
      }
    },
    [router, setPathState]
  );
}

export interface LocationState {
  pathname: string;
  search: string;
  hash: string;
  state: any;
  key: string;
}

export function useLocation(): LocationState {
  const pathname = useNextPathname() || '/';
  const { getPathState } = useContext(NavigationStateContext);

  const state = useMemo(() => {
    return getPathState(pathname);
  }, [getPathState, pathname]);

  const [search, setSearch] = useState('');
  const [hash, setHash] = useState('');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setSearch(window.location.search || '');
      setHash(window.location.hash || '');
    }
  }, [pathname]);

  return {
    pathname,
    search: typeof window !== 'undefined' ? (window.location.search || search) : search,
    hash: typeof window !== 'undefined' ? (window.location.hash || hash) : hash,
    state,
    key: pathname,
  };
}

export function useParams<T extends Record<string, string | string[] | undefined> = Record<string, string | string[] | undefined>>(): T {
  const params = useNextParams();
  return (params || {}) as T;
}

export function useSearchParams(): [URLSearchParams, (params: URLSearchParams | Record<string, string>) => void] {
  const router = useNextRouter();
  const pathname = useNextPathname() || '/';

  const [searchParams, setSearchParamsState] = useState<URLSearchParams>(() => {
    if (typeof window !== 'undefined') {
      return new URLSearchParams(window.location.search);
    }
    return new URLSearchParams('');
  });

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setSearchParamsState(new URLSearchParams(window.location.search));
    }
  }, [pathname]);

  const setSearchParams = useCallback(
    (newParams: URLSearchParams | Record<string, string>) => {
      const sp = newParams instanceof URLSearchParams ? newParams : new URLSearchParams(newParams);
      router.push(`${pathname}?${sp.toString()}`);
      setSearchParamsState(sp);
    },
    [router, pathname]
  );

  const currentParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : searchParams;

  return [currentParams, setSearchParams];
}

export const Navigate: React.FC<{ to: string; replace?: boolean; state?: any }> = ({ to, replace, state }) => {
  const navigate = useNavigate();
  useEffect(() => {
    navigate(to, { replace, state });
  }, [navigate, to, replace, state]);
  return null;
};

export interface LinkProps extends Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> {
  to?: string;
  href?: string;
  replace?: boolean;
}

export const Link = forwardRef<HTMLAnchorElement, LinkProps>(({ to, href, children, ...props }, ref) => {
  const target = to || href || '#';
  return (
    <NextLink ref={ref} href={target} {...(props as any)}>
      {children}
    </NextLink>
  );
});
Link.displayName = 'Link';

export const Outlet: React.FC<{ context?: any; children?: React.ReactNode }> = ({ children }) => {
  return <>{children}</>;
};

export const BrowserRouter: React.FC<{ children?: React.ReactNode }> = ({ children }) => <>{children}</>;
export const Routes: React.FC<{ children?: React.ReactNode }> = ({ children }) => <>{children}</>;
export const Route: React.FC<any> = () => null;

export default {
  useNavigate,
  useLocation,
  useParams,
  useSearchParams,
  Navigate,
  Link,
  Outlet,
  BrowserRouter,
  Routes,
  Route,
  NavigationProvider,
};
