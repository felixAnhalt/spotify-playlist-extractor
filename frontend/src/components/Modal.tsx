import React from "react";

interface ModalProps {
  open: boolean;
  children: React.ReactNode;
}

const Modal: React.FC<ModalProps> = ({ open, children }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-neutral-900/30 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-primary-50 p-8 rounded-xl min-w-80 max-w-md shadow-2xl border-primary-700 cartoon-card border-cartoon-3 shadow-cartoon">
        {children}
      </div>
    </div>
  );
};

export default Modal;
