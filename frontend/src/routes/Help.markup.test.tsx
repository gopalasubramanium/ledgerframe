// SPDX-License-Identifier: AGPL-3.0-or-later
//
// The served-markup renderer (page-help §9-bis-11(b)).
//
// The point of these tests is not that bold renders bold. It is that the renderer CANNOT inject
// markup, that it never drops authored text, and that it stays in step with the backend subset
// defined in `app/services/help_markup.py`.

// The CROSS-LANGUAGE pin (this renderer vs `app/services/help_markup.py`) and the
// no-`dangerouslySetInnerHTML` guard live on the PYTHON side, in
// `tests/unit/test_help_markup.py`. They have to read both files, the backend guards already
// read frontend sources (`nav.ts`, and the whole `src/**/*.tsx` sweep in the accuracy corpus),
// and the alternative was widening the app tsconfig's `types` to include `node` for every file
// in `src/` — a build-wide change to accommodate two assertions.

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { HelpProse } from './helpMarkup';

describe('the served-markup renderer', () => {
  it('renders bold and italic as real elements', () => {
    render(<HelpProse text="Net worth is **derived**, never *entered*." />);
    expect(screen.getByText('derived').tagName).toBe('STRONG');
    expect(screen.getByText('entered').tagName).toBe('EM');
  });

  it('renders headings and lists as structure', () => {
    const { container } = render(
      <HelpProse text={'## How to read it\n\n- First point\n- Second point'} />,
    );
    expect(container.querySelector('.help__prosehead')?.textContent).toBe('How to read it');
    expect(container.querySelectorAll('.help__proselist li')).toHaveLength(2);
  });

  it('joins wrapped lines into ONE paragraph and splits on the blank line', () => {
    // Served strings are authored across source lines; a renderer that made one paragraph per
    // source line would put a break wherever the Python happened to wrap.
    const { container } = render(<HelpProse text={'one\ntwo\n\nthree'} />);
    const paras = container.querySelectorAll('.help__prosepara');
    expect(paras).toHaveLength(2);
    expect(paras[0].textContent).toBe('one two');
  });

  it('NEVER injects HTML — a served angle bracket stays text', () => {
    // The safety property, stated as a test. Even if a string carrying markup reached the served
    // shape (the backend validator rejects it, but defence in depth is the point), the renderer
    // has no path that turns it into an element.
    const { container } = render(<HelpProse text={'<img src=x onerror=alert(1)> and <b>hi</b>'} />);
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('b')).toBeNull();
    expect(container.textContent).toContain('<img src=x onerror=alert(1)>');
  });

  it('drops no authored text, whatever the line shape', () => {
    const src = '## Head\n\nplain line\n- item\ntrailing prose';
    const rendered = render(<HelpProse text={src} />).container.textContent ?? '';
    for (const fragment of ['Head', 'plain line', 'item', 'trailing prose']) {
      expect(rendered).toContain(fragment);
    }
  });

  it('handles empty and marker-free strings without emitting empty blocks', () => {
    const { container } = render(<HelpProse text="" />);
    expect(container.querySelectorAll('.help__prosepara')).toHaveLength(0);

    // The parser is an internal — it is exercised THROUGH the component, which is the only
    // export. One export per module keeps react-refresh working and keeps the test honest about
    // what the page actually uses.
    const plain = render(<HelpProse text="just prose" />).container;
    expect(plain.querySelectorAll('.help__prosepara')).toHaveLength(1);
    expect(plain.textContent).toBe('just prose');
  });

  it('leaves an underscore identifier alone — it is not emphasis in this subset', () => {
    render(<HelpProse text="the home_layout setting" />);
    expect(screen.getByText(/home_layout/)).toBeTruthy();
  });
});
