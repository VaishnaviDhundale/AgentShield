import React, { useEffect, useState } from 'react';
import {
  FolderTree,
  Folder,
  File,
  FileCode,
  FileText,
  Database,
  Lock,
  RefreshCw,
  RotateCcw,
  CheckCircle2,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';
import { SandboxFileEntry } from '../types';

export const SandboxExplorer: React.FC = () => {
  const [tree, setTree] = useState<SandboxFileEntry[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [resetting, setResetting] = useState<boolean>(false);
  const [resetSuccess, setResetSuccess] = useState<boolean>(false);

  const loadTree = async () => {
    setLoading(true);
    try {
      const res = await api.getSandboxTree();
      setTree(res.tree);
      // Auto select first file if available
      const firstFile = res.tree.find((item) => item.type === 'file');
      if (firstFile && !selectedFile) {
        handleSelectFile(firstFile.path);
      }
    } catch (err) {
      console.error('Failed to load sandbox tree:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectFile = async (filePath: string) => {
    setSelectedFile(filePath);
    try {
      const res = await api.getSandboxFile(filePath);
      setFileContent(res.content);
      setFileSize(res.size_bytes);
    } catch (err) {
      console.error(`Failed to read file ${filePath}:`, err);
      setFileContent('// Error reading file or binary file format');
    }
  };

  const handleResetSandbox = async () => {
    setResetting(true);
    try {
      await api.resetSandbox();
      setResetSuccess(true);
      setTimeout(() => setResetSuccess(false), 3000);
      await loadTree();
      if (selectedFile) {
        await handleSelectFile(selectedFile);
      }
    } catch (err) {
      console.error('Failed to reset sandbox:', err);
    } finally {
      setResetting(false);
    }
  };

  useEffect(() => {
    loadTree();
  }, []);

  const getFileIcon = (name: string, type: string) => {
    if (type === 'directory') return <Folder className="w-4 h-4 text-cyan-400" />;
    if (name.endsWith('.py')) return <FileCode className="w-4 h-4 text-emerald-400" />;
    if (name.endsWith('.db') || name.endsWith('.sqlite')) return <Database className="w-4 h-4 text-amber-400" />;
    if (name.includes('.env') || name.includes('secret') || name.includes('key')) return <Lock className="w-4 h-4 text-rose-400" />;
    return <FileText className="w-4 h-4 text-slate-400" />;
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-inner">
            <FolderTree className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                Isolated Sandbox Filesystem Explorer
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                Safe Jail Boundary
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Strictly restricted to the isolated sandbox environment. Host filesystem is completely invisible.
            </p>
          </div>
        </div>

        {/* Reset Sandbox Action */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
          {resetSuccess && (
            <span className="text-xs font-mono text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Fixtures Restored!</span>
            </span>
          )}
          <button
            disabled={resetting}
            onClick={handleResetSandbox}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all flex items-center gap-1.5 active:scale-95 disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`} />
            <span>Reset Sandbox to Pristine Fixtures</span>
          </button>
        </div>
      </div>

      {/* Two Column Layout: File Tree vs File Content Viewer */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left 1 Col: File Tree */}
        <div className="bg-[#111726] border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
            <span className="text-xs font-bold text-slate-300 uppercase font-mono flex items-center gap-1.5">
              <FolderTree className="w-4 h-4 text-cyan-400" />
              <span>Sandbox Root</span>
            </span>
            <button
              onClick={loadTree}
              className="p-1 text-slate-400 hover:text-cyan-400 transition-colors"
              title="Refresh tree"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-1 overflow-y-auto max-h-[500px] scrollbar-thin">
            {tree.map((entry) => {
              const isSelected = selectedFile === entry.path;

              if (entry.type === 'directory') {
                return (
                  <div
                    key={entry.path}
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-mono text-slate-400 bg-slate-900/40"
                  >
                    {getFileIcon(entry.name, entry.type)}
                    <span className="font-semibold text-slate-300">{entry.path}/</span>
                  </div>
                );
              }

              return (
                <button
                  key={entry.path}
                  onClick={() => handleSelectFile(entry.path)}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-mono transition-all text-left ${
                    isSelected
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                      : 'text-slate-300 hover:bg-[#141b2d]'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    {getFileIcon(entry.name, entry.type)}
                    <span className="truncate">{entry.name}</span>
                  </div>
                  <span className="text-[10px] text-slate-500 shrink-0">
                    {entry.size > 0 ? `${entry.size}B` : ''}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right 2 Cols: Safe File Content Viewer */}
        <div className="md:col-span-2 bg-[#111726] border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
            <div className="flex items-center gap-2 font-mono text-xs text-slate-300 truncate">
              <span className="text-slate-500">File:</span>
              <span className="font-bold text-cyan-300 truncate">{selectedFile || 'None'}</span>
              {fileSize > 0 && (
                <span className="text-[10px] text-slate-500">({fileSize} bytes)</span>
              )}
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              Read-Only Safe View
            </span>
          </div>

          <div className="flex-1 bg-[#0a0d14] border border-slate-800 rounded-xl p-4 overflow-x-auto max-h-[500px] scrollbar-thin">
            {fileContent ? (
              <pre className="text-xs font-mono text-slate-200 leading-relaxed whitespace-pre-wrap">
                {fileContent}
              </pre>
            ) : (
              <div className="py-20 text-center text-slate-600 font-mono text-xs">
                Select a file from the tree to preview contents.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
