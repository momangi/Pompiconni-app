import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import TextAlign from '@tiptap/extension-text-align';
import { Bold, Italic, List, AlignLeft, AlignCenter, AlignRight, Type } from 'lucide-react';
import { Button } from '../ui/button';
import { ToggleGroup, ToggleGroupItem } from '../ui/toggle-group';

// Custom CSS classes for font sizes
const fontSizeStyles = `
  .ProseMirror .font-size-s { font-size: 0.875rem; line-height: 1.4; }
  .ProseMirror .font-size-m { font-size: 1rem; line-height: 1.5; }
  .ProseMirror .font-size-l { font-size: 1.25rem; line-height: 1.6; }
  .ProseMirror { min-height: 200px; outline: none; }
  .ProseMirror p { margin-bottom: 0.75rem; }
  .ProseMirror ul { list-style-type: disc; padding-left: 1.5rem; margin-bottom: 0.75rem; }
  .ProseMirror li { margin-bottom: 0.25rem; }
  .ProseMirror p.text-left { text-align: left; }
  .ProseMirror p.text-center { text-align: center; }
  .ProseMirror p.text-right { text-align: right; }
`;

const SceneTextEditor = ({ content, onChange, placeholder = "Scrivi il testo della scena..." }) => {
  const [fontSize, setFontSize] = React.useState('M');

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Disable features not allowed
        heading: false,
        codeBlock: false,
        code: false,
        blockquote: false,
        horizontalRule: false,
        hardBreak: true,
        // Keep allowed features
        bold: true,
        italic: true,
        bulletList: true,
        listItem: true,
        paragraph: true,
      }),
      TextAlign.configure({
        types: ['paragraph'],
        alignments: ['left', 'center', 'right'],
      }),
    ],
    content: content || '',
    onUpdate: ({ editor }) => {
      // Get HTML and add font-size class to paragraphs
      let html = editor.getHTML();
      // Apply current font size to all paragraphs without a font-size class
      html = html.replace(/<p(?![^>]*class="[^"]*font-size)/g, `<p class="font-size-${fontSize.toLowerCase()}"`);
      onChange(html);
    },
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none p-4 min-h-[200px]',
      },
      // Prevent paste of formatted HTML - strip to plain text
      handlePaste: (view, event) => {
        event.preventDefault();
        const text = event.clipboardData?.getData('text/plain') || '';
        // Insert plain text only
        const { state, dispatch } = view;
        const { tr, selection } = state;
        const { from, to } = selection;
        dispatch(tr.insertText(text, from, to));
        return true;
      },
    },
  });

  // Apply font size to all content
  const applyFontSize = (size) => {
    setFontSize(size);
    if (editor) {
      // Re-trigger update to apply new font size
      const html = editor.getHTML();
      const newHtml = html.replace(/font-size-[sml]/g, `font-size-${size.toLowerCase()}`);
      onChange(newHtml);
    }
  };

  if (!editor) {
    return null;
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Inject styles */}
      <style>{fontSizeStyles}</style>
      
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1 p-2 border-b bg-gray-50">
        {/* Bold */}
        <Button
          type="button"
          variant={editor.isActive('bold') ? 'default' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleBold().run()}
          title="Grassetto"
        >
          <Bold className="w-4 h-4" />
        </Button>

        {/* Italic */}
        <Button
          type="button"
          variant={editor.isActive('italic') ? 'default' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          title="Corsivo"
        >
          <Italic className="w-4 h-4" />
        </Button>

        {/* Bullet List */}
        <Button
          type="button"
          variant={editor.isActive('bulletList') ? 'default' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          title="Elenco puntato"
        >
          <List className="w-4 h-4" />
        </Button>

        <div className="w-px h-6 bg-gray-300 mx-1" />

        {/* Alignment */}
        <Button
          type="button"
          variant={editor.isActive({ textAlign: 'left' }) ? 'default' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().setTextAlign('left').run()}
          title="Allinea a sinistra"
        >
          <AlignLeft className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant={editor.isActive({ textAlign: 'center' }) ? 'default' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().setTextAlign('center').run()}
          title="Centra"
        >
          <AlignCenter className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          variant={editor.isActive({ textAlign: 'right' }) ? 'default' : 'ghost'}
          size="sm"
          onClick={() => editor.chain().focus().setTextAlign('right').run()}
          title="Allinea a destra"
        >
          <AlignRight className="w-4 h-4" />
        </Button>

        <div className="w-px h-6 bg-gray-300 mx-1" />

        {/* Font Size */}
        <div className="flex items-center gap-1">
          <Type className="w-4 h-4 text-gray-500" />
          <ToggleGroup type="single" value={fontSize} onValueChange={(val) => val && applyFontSize(val)}>
            <ToggleGroupItem value="S" className="text-xs px-2 h-8">S</ToggleGroupItem>
            <ToggleGroupItem value="M" className="text-sm px-2 h-8">M</ToggleGroupItem>
            <ToggleGroupItem value="L" className="text-base px-2 h-8">L</ToggleGroupItem>
          </ToggleGroup>
        </div>
      </div>

      {/* Editor Content */}
      <div className="bg-white">
        <EditorContent editor={editor} />
        {!content && (
          <div className="absolute top-16 left-4 text-gray-400 pointer-events-none">
            {placeholder}
          </div>
        )}
      </div>
    </div>
  );
};

export default SceneTextEditor;
