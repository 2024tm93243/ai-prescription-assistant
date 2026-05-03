import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import './PrescriptionUpload.css';

/**
 * PrescriptionUpload - Drag-and-drop file upload component
 */
function PrescriptionUpload({ onUpload, isLoading }) {
  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length > 0 && !isLoading) {
        onUpload(acceptedFiles[0]);
      }
    },
    [onUpload, isLoading]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.bmp', '.tiff', '.tif'],
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    disabled: isLoading,
  });

  return (
    <div
      {...getRootProps()}
      className={`prescription-upload ${isDragActive ? 'drag-active' : ''} ${
        isLoading ? 'loading' : ''
      }`}
    >
      <input {...getInputProps()} />
      
      {isLoading ? (
        <div className="upload-loading">
          <div className="spinner"></div>
          <p>Processing prescription...</p>
        </div>
      ) : isDragActive ? (
        <div className="upload-active">
          <span className="upload-icon">📥</span>
          <p>Drop the prescription here</p>
        </div>
      ) : (
        <div className="upload-idle">
          <span className="upload-icon">📄</span>
          <p className="upload-text">Drag & drop a prescription image here</p>
          <p className="upload-subtext">or click to select a file</p>
          <p className="upload-formats">Supported: JPG, PNG, PDF, TIFF, BMP</p>
        </div>
      )}
    </div>
  );
}

export default PrescriptionUpload;
