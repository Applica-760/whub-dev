import '@mantine/core/styles.css';
import './theme/global.css';

import { MantineProvider } from '@mantine/core';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';

import { App } from './App';
import { theme } from './theme/theme';

createRoot(document.getElementById('root')!).render(
  <MantineProvider theme={theme} defaultColorScheme="light">
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </MantineProvider>,
);
