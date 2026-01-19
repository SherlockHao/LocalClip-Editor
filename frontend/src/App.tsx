import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import TaskDashboard from './pages/TaskDashboard';
import TaskEditorOld from './pages/TaskEditorOld';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<TaskDashboard />} />
        <Route path="/tasks/:taskId" element={<TaskEditorOld />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
