import type { Preview } from '@storybook/react'
// The Marginalia design system is the source of truth for every story.
import '../src/system.css'
import '../src/screens.css'

const preview: Preview = {
  parameters: {
    layout: 'padded',
    controls: { expanded: true },
  },
}

export default preview
