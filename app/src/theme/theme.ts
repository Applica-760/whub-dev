import { createTheme } from '@mantine/core';

export const theme = createTheme({
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Helvetica Neue", "Hiragino Sans", sans-serif',
  defaultRadius: 'md',
  radius: {
    md: '12px',
  },
  shadows: {
    xs: 'none',
    sm: 'none',
    md: 'none',
    lg: 'none',
    xl: 'none',
  },
});
