import { cloneElement, isValidElement } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { useLicenseStatus } from '../hooks/useLicenseStatus';

const READONLY_MESSAGE = '试用期已结束，请激活正式版后再操作';

/**
 * 只读模式 hook：返回 { readOnly, message } 给业务组件按需禁用功能。
 */
export const useReadOnly = () => {
  const { info } = useLicenseStatus();
  return {
    readOnly: info.read_only_mode,
    message: READONLY_MESSAGE,
  };
};

/**
 * <ReadOnlyButton> 包装器：
 *   - 接收单个子元素（通常是 <button>）
 *   - 只读模式下自动添加 disabled、opacity、title 提示
 *   - 非只读模式直接渲染原子元素
 *
 * 用法：
 *   <ReadOnlyButton>
 *     <button onClick={openModal}>新增客户</button>
 *   </ReadOnlyButton>
 */
interface ReadOnlyButtonProps {
  children: ReactNode;
  /** 自定义提示文案，默认"试用期已结束，请激活正式版后再操作" */
  tooltip?: string;
}

export const ReadOnlyButton = ({ children, tooltip }: ReadOnlyButtonProps) => {
  const { readOnly } = useReadOnly();
  if (!readOnly) return <>{children}</>;

  // 仅处理单个 React 元素
  if (!isValidElement(children)) return <>{children}</>;

  const el = children as ReactElement<any>;
  const existingClass = (el.props.className as string) || '';
  return cloneElement(el, {
    disabled: true,
    title: tooltip || READONLY_MESSAGE,
    onClick: (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
    },
    className: `${existingClass} opacity-50 cursor-not-allowed`.trim(),
  });
};
