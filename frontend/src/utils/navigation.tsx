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
  state: any;
  setState: (state: any) => void;
}

const NavigationStateContext = createContext<NavigationStateContextType>({
  state: null,
  setState: () => {},
});

export const NavigationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<any>(null);
  const pathname = useNextPathname();

  // Restore navigation state from sessionStorage or history on pathname change
  useEffect(() => {
    if (typeof window !== 'undefined' && pathname) {
      try {
        const stored = sessionStorage.getItem(`__nav_state_${pathname}`);
        if (stored) {
          setState(JSON.parse(stored));
        } else if (window.history.state && window.history.state.usr) {
          setState(window.history.state.usr);
        }
      } catch {
        // ignore
      }
    }
  }, [pathname]);

  return (
    <NavigationStateContext.Provider value={{ state, setState }}>
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
  const { setState } = useContext(NavigationStateContext);

  return useCallback(
    (to: string | number, options?: NavigateOptions) => {
      if (typeof to === 'number') {
        if (typeof window !== 'undefined') {
          window.history.go(to);
        }
        return;
      }

      if (options?.state !== undefined) {
        setState(options.state);
        if (typeof window !== 'undefined') {
          try {
            const cleanPath = to.split('?')[0];
            sessionStorage.setItem(`__nav_state_${cleanPath}`, JSON.stringify(options.state));
            const currentHistoryState = window.history.state || {};
            window.history.replaceState({ ...currentHistoryState, usr: options.state }, '', window.location.href);
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
    [router, setState]
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
  const { state } = useContext(NavigationStateContext);

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
