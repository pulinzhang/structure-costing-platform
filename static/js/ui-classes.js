/**
 * 上传页 / 零件列表共用 Tailwind 类（原 style.css 业务段迁出）。
 * 交互钩子名（die-type-select）保留在类串首位，供 querySelector。
 */

export const UPLOAD_LABEL =
    'block text-[10px] font-semibold uppercase tracking-[0.1em] text-[#616161]';

export const UPLOAD_INPUT =
    'appearance-none w-full h-[42px] pl-3.5 pr-11 bg-[#050505] border border-[#2d2d2d] rounded-[3px] text-[11px] text-[#b0b0b0] cursor-pointer transition-all duration-150 hover:border-[#404040] focus:outline-none focus:border-[#d32f2f] focus:text-white focus:shadow-[0_0_0_1px_rgba(211,47,47,0.15)]';

export const UPLOAD_DROPZONE =
    'border border-dashed border-[#282828] bg-[#080808] shadow-[inset_0_1px_4px_rgba(0,0,0,0.5)] rounded-[2px] px-6 py-7 text-center cursor-pointer transition-all duration-200 hover:border-[#3a3a3a] hover:bg-[#0b0b0b] data-[dropzone-state=drag]:border-[#d32f2f] data-[dropzone-state=drag]:border-solid data-[dropzone-state=drag]:bg-[#100808] data-[dropzone-state=drag]:shadow-[inset_0_1px_8px_rgba(211,47,47,0.1),0_0_0_1px_rgba(211,47,47,0.2),0_0_14px_rgba(211,47,47,0.07)] data-[dropzone-state=file]:border-[#d32f2f] data-[dropzone-state=file]:border-solid data-[dropzone-state=file]:bg-[#100808] data-[dropzone-state=file]:shadow-[inset_0_1px_6px_rgba(211,47,47,0.07),0_0_0_1px_rgba(211,47,47,0.12)]';

export const BTN_GHOST =
    'inline-flex items-center gap-1.5 bg-transparent text-[#9e9e9e] border border-[#2c2c2c] px-5 py-2 rounded text-[13px] font-medium transition-all duration-200 hover:text-white hover:border-[#9e9e9e]';

export const BTN_UPLOAD_SUBMIT =
    'inline-flex items-center gap-2 bg-[#d32f2f] text-white border border-[#d32f2f] px-7 h-11 rounded-[2px] text-[11px] font-bold tracking-[0.1em] transition-all duration-150 hover:bg-[#b71c1c] hover:border-[#b71c1c] hover:shadow-[0_0_16px_rgba(211,47,47,0.5)] disabled:bg-[#262626] disabled:border-[#2c2c2c] disabled:text-[#616161] disabled:shadow-none disabled:cursor-not-allowed disabled:opacity-30 disabled:pointer-events-none';

export const BTN_FILE_SELECT =
    'inline-flex items-center gap-1.5 bg-[#0d0d0d] text-[#707070] border border-[#2a2a2a] px-4 h-9 rounded-[2px] text-[10px] font-semibold tracking-[0.08em] transition-all duration-150 hover:border-[#d32f2f] hover:text-[#d32f2f]';

export const DIE_TYPE_SELECT =
    'die-type-select appearance-none h-7 pl-2.5 pr-8 w-auto min-w-[9rem] bg-[#0c0c0c] border border-transparent rounded-[2px] text-[10px] font-normal tracking-[0.08em] text-[#888888] cursor-pointer outline-none transition-all duration-150 hover:border-[#2a2a2a] hover:bg-[#0e0e0e] hover:text-[#bbbbbb] focus:border-[#d32f2f] focus:bg-[#0e0e0e] focus:text-[#bbbbbb] focus:shadow-[0_0_0_2px_rgba(211,47,47,0.12)]';

export const BTN_SAVE_DEFAULT =
    'inline-flex items-center justify-center gap-2 max-w-[260px] h-10 px-8 bg-[#111111] border border-[#262626] rounded-[2px] text-[#777777] text-[11px] font-medium tracking-[0.15em] uppercase cursor-pointer transition-all duration-200 hover:bg-[#d32f2f] hover:border-[#d32f2f] hover:text-white hover:shadow-[0_0_20px_rgba(211,47,47,0.4)]';

export const BTN_SAVE_ACTIVE =
    'inline-flex items-center justify-center gap-2 w-full h-10 bg-[#1c1c1c] border border-[#d32f2f] rounded-[2px] text-white text-[11px] font-medium tracking-[0.15em] uppercase cursor-pointer shadow-[0_0_16px_rgba(211,47,47,0.3)] transition-all duration-200 hover:bg-[#d32f2f] hover:shadow-[0_0_20px_rgba(211,47,47,0.4)]';

export const SKETCH_THUMBNAIL =
    'relative w-9 h-9 rounded bg-[#141414] border border-[#2c2c2c] overflow-hidden cursor-pointer shrink-0 flex items-center justify-center transition-colors duration-200 hover:border-[#d32f2f] group/sketch';

export const SKETCH_PLACEHOLDER =
    'w-9 h-9 rounded bg-[#262626] border border-dashed border-[#2c2c2c] flex items-center justify-center shrink-0 text-[#616161]';

export const ZOOM_OVERLAY =
    'absolute inset-0 bg-black/65 flex items-center justify-center opacity-0 transition-opacity duration-200 rounded group-hover/sketch:opacity-100 text-white [&_svg]:w-3.5 [&_svg]:h-3.5 [&_svg]:text-white';

export const BRABUS_PANEL =
    'bg-[#111111] border-t border-[#282828] border-l border-[#262626] border-r border-[#181818] border-b border-[#101010] overflow-hidden shadow-[2px_2px_8px_rgba(0,0,0,0.5),inset_-1px_-1px_0_rgba(255,255,255,0.015)]';

export const BRABUS_PANEL_HEADER =
    'px-4 py-2.5 bg-[#0c0c0c] border-b border-[#181818]';

export const BRABUS_SECTION_HEADER =
    'px-4 py-2.5 bg-[#0c0c0c] border-t border-[#262626] border-l border-[#282828] border-r border-[#181818] border-b border-[#161616] shadow-[2px_2px_8px_rgba(0,0,0,0.4),inset_-1px_0_0_rgba(255,255,255,0.012)]';

export const BRABUS_TABLE_WRAPPER =
    'bg-[#111111] border-l border-[#252525] border-r border-[#161616] border-b border-[#0f0f0f]';
