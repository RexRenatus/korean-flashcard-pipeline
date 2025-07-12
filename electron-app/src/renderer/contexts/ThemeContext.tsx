import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { createTheme, ThemeProvider as MuiThemeProvider, PaletteMode } from '@mui/material';
import { blue, grey, green, orange, red } from '@mui/material/colors';

interface ThemeContextType {
  mode: PaletteMode;
  toggleTheme: () => void;
  setTheme: (mode: PaletteMode) => void;
  primaryColor: string;
  setPrimaryColor: (color: string) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

const colorOptions = {
  blue: blue,
  green: green,
  orange: orange,
  red: red,
};

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [mode, setMode] = useState<PaletteMode>('light');
  const [primaryColor, setPrimaryColor] = useState<string>('blue');

  // Load theme preferences from localStorage
  useEffect(() => {
    const savedMode = localStorage.getItem('themeMode') as PaletteMode;
    const savedColor = localStorage.getItem('themePrimaryColor');
    
    if (savedMode) {
      setMode(savedMode);
    } else {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setMode(prefersDark ? 'dark' : 'light');
    }
    
    if (savedColor && savedColor in colorOptions) {
      setPrimaryColor(savedColor);
    }
  }, []);

  // Save theme preferences
  useEffect(() => {
    localStorage.setItem('themeMode', mode);
  }, [mode]);

  useEffect(() => {
    localStorage.setItem('themePrimaryColor', primaryColor);
  }, [primaryColor]);

  const theme = useMemo(() => {
    const primaryColorPalette = colorOptions[primaryColor as keyof typeof colorOptions] || blue;
    
    return createTheme({
      palette: {
        mode,
        primary: {
          main: primaryColorPalette[mode === 'light' ? 600 : 400],
          light: primaryColorPalette[mode === 'light' ? 400 : 300],
          dark: primaryColorPalette[mode === 'light' ? 800 : 600],
        },
        secondary: {
          main: mode === 'light' ? orange[600] : orange[400],
        },
        background: {
          default: mode === 'light' ? '#f5f5f5' : '#121212',
          paper: mode === 'light' ? '#ffffff' : '#1e1e1e',
        },
        text: {
          primary: mode === 'light' ? grey[900] : grey[100],
          secondary: mode === 'light' ? grey[700] : grey[400],
        },
      },
      typography: {
        fontFamily: '"Roboto", "Noto Sans KR", "Helvetica", "Arial", sans-serif',
        h1: {
          fontSize: '2.5rem',
          fontWeight: 500,
        },
        h2: {
          fontSize: '2rem',
          fontWeight: 500,
        },
        h3: {
          fontSize: '1.75rem',
          fontWeight: 500,
        },
        h4: {
          fontSize: '1.5rem',
          fontWeight: 500,
        },
        h5: {
          fontSize: '1.25rem',
          fontWeight: 500,
        },
        h6: {
          fontSize: '1rem',
          fontWeight: 500,
        },
      },
      shape: {
        borderRadius: 8,
      },
      components: {
        MuiButton: {
          styleOverrides: {
            root: {
              textTransform: 'none',
              fontWeight: 500,
            },
          },
        },
        MuiCard: {
          styleOverrides: {
            root: {
              boxShadow: mode === 'light' 
                ? '0 2px 8px rgba(0,0,0,0.1)' 
                : '0 2px 8px rgba(0,0,0,0.3)',
              transition: 'box-shadow 0.3s ease-in-out',
              '&:hover': {
                boxShadow: mode === 'light'
                  ? '0 4px 16px rgba(0,0,0,0.15)'
                  : '0 4px 16px rgba(0,0,0,0.4)',
              },
            },
          },
        },
        MuiPaper: {
          styleOverrides: {
            root: {
              backgroundImage: 'none',
            },
          },
        },
        MuiDrawer: {
          styleOverrides: {
            paper: {
              backgroundImage: 'none',
              borderRight: mode === 'light' 
                ? '1px solid rgba(0, 0, 0, 0.12)' 
                : '1px solid rgba(255, 255, 255, 0.12)',
            },
          },
        },
        MuiAppBar: {
          styleOverrides: {
            root: {
              backgroundImage: 'none',
              boxShadow: mode === 'light'
                ? '0 1px 3px rgba(0,0,0,0.12)'
                : '0 1px 3px rgba(0,0,0,0.5)',
            },
          },
        },
        MuiTableCell: {
          styleOverrides: {
            root: {
              borderBottom: mode === 'light'
                ? '1px solid rgba(224, 224, 224, 1)'
                : '1px solid rgba(81, 81, 81, 1)',
            },
          },
        },
        MuiChip: {
          styleOverrides: {
            root: {
              fontWeight: 500,
            },
          },
        },
      },
    });
  }, [mode, primaryColor]);

  const toggleTheme = () => {
    setMode(prevMode => prevMode === 'light' ? 'dark' : 'light');
  };

  const setTheme = (newMode: PaletteMode) => {
    setMode(newMode);
  };

  const value = {
    mode,
    toggleTheme,
    setTheme,
    primaryColor,
    setPrimaryColor,
  };

  return (
    <ThemeContext.Provider value={value}>
      <MuiThemeProvider theme={theme}>
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
};