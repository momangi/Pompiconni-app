import { Extension } from '@tiptap/core';

// Custom FontSize extension that only allows S, M, L values
export const FontSize = Extension.create({
  name: 'fontSize',

  addOptions() {
    return {
      types: ['textStyle'],
      sizes: {
        S: 'font-size-s',
        M: 'font-size-m', 
        L: 'font-size-l',
      },
    };
  },

  addGlobalAttributes() {
    return [
      {
        types: ['paragraph'],
        attributes: {
          fontSize: {
            default: 'M',
            parseHTML: element => {
              if (element.classList.contains('font-size-s')) return 'S';
              if (element.classList.contains('font-size-l')) return 'L';
              return 'M';
            },
            renderHTML: attributes => {
              if (!attributes.fontSize || attributes.fontSize === 'M') {
                return { class: 'font-size-m' };
              }
              return { class: `font-size-${attributes.fontSize.toLowerCase()}` };
            },
          },
        },
      },
    ];
  },

  addCommands() {
    return {
      setFontSize: (size) => ({ chain }) => {
        if (!['S', 'M', 'L'].includes(size)) return false;
        return chain()
          .updateAttributes('paragraph', { fontSize: size })
          .run();
      },
    };
  },
});

export default FontSize;
