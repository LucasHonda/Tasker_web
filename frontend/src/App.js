import React, { useState, useEffect, createContext, useContext } from 'react';
import './App.css';
import axios from 'axios';
import { Calendar, Plus, CheckCircle, Circle, Edit3, Trash2, Bell, Filter, LayoutGrid, List, LogOut, User, Settings } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const login = (redirectUrl) => {
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`);
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      setUser(null);
    }
  };

  const processSession = async (sessionId) => {
    try {
      const response = await axios.post(`${API}/auth/session`, {
        session_id: sessionId
      });
      setUser(response.data);
      return response.data;
    } catch (error) {
      console.error('Session processing error:', error);
      throw error;
    }
  };

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      setUser(null);
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const hash = window.location.hash;
      const sessionIdMatch = hash.match(/session_id=([^&]+)/);
      
      if (sessionIdMatch) {
        const sessionId = sessionIdMatch[1];
        try {
          await processSession(sessionId);
          // Clean URL
          window.history.replaceState({}, document.title, window.location.pathname);
        } catch (error) {
          console.error('Session processing failed:', error);
        }
      } else {
        await checkAuth();
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

// Login Component
const LoginPage = () => {
  const { login } = useAuth();

  const handleLogin = () => {
    const redirectUrl = `${window.location.origin}/dashboard`;
    login(redirectUrl);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <Calendar className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Calendar & Tasks</h1>
          <p className="text-gray-600 mb-8">Manage your schedule and tasks in one beautiful place</p>
          
          <button
            onClick={handleLogin}
            className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-blue-600 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl"
          >
            Sign in with Google
          </button>
          
          <div className="mt-8 grid grid-cols-3 gap-4 text-sm text-gray-500">
            <div className="text-center">
              <Calendar className="w-8 h-8 mx-auto mb-2 text-blue-500" />
              <p>Calendar Integration</p>
            </div>
            <div className="text-center">
              <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
              <p>Task Management</p>
            </div>
            <div className="text-center">
              <Bell className="w-8 h-8 mx-auto mb-2 text-orange-500" />
              <p>Smart Reminders</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Task Components
const TaskForm = ({ task, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    title: task?.title || '',
    description: task?.description || '',
    category: task?.category || 'General',
    priority: task?.priority || 'Medium',
    due_date: task?.due_date ? new Date(task.due_date).toISOString().slice(0, 16) : '',
    reminder: task?.reminder ? new Date(task.reminder).toISOString().slice(0, 16) : ''
  });

  const [availableCategories, setAvailableCategories] = useState(['General', 'Work', 'Personal', 'Health', 'Shopping', 'Finance']);
  const [showNewCategory, setShowNewCategory] = useState(false);
  const [newCategory, setNewCategory] = useState('');
  const priorities = ['Low', 'Medium', 'High'];

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/tasks/categories`);
      const userCategories = response.data;
      const defaultCategories = ['General', 'Work', 'Personal', 'Health', 'Shopping', 'Finance'];
      const allCategories = [...new Set([...defaultCategories, ...userCategories])];
      setAvailableCategories(allCategories);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const handleAddCategory = () => {
    if (newCategory.trim() && !availableCategories.includes(newCategory.trim())) {
      const updatedCategories = [...availableCategories, newCategory.trim()];
      setAvailableCategories(updatedCategories);
      setFormData({...formData, category: newCategory.trim()});
      setNewCategory('');
      setShowNewCategory(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const submitData = {
      ...formData,
      due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null,
      reminder: formData.reminder ? new Date(formData.reminder).toISOString() : null
    };
    onSubmit(submitData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl p-6 w-full max-w-lg max-h-90vh overflow-y-auto">
        <h3 className="text-xl font-bold mb-4">{task ? 'Edit Task' : 'New Task'}</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({...formData, title: e.target.value})}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Task title..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows="3"
              placeholder="Task description..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <div className="flex gap-2">
                <select
                  value={formData.category}
                  onChange={(e) => {
                    if (e.target.value === '_add_new_') {
                      setShowNewCategory(true);
                    } else {
                      setFormData({...formData, category: e.target.value});
                    }
                  }}
                  className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {availableCategories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                  <option value="_add_new_">+ Add New Category</option>
                </select>
              </div>
              
              {showNewCategory && (
                <div className="mt-2 flex gap-2">
                  <input
                    type="text"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    placeholder="New category name..."
                    className="flex-1 p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    onKeyPress={(e) => e.key === 'Enter' && handleAddCategory()}
                  />
                  <button
                    type="button"
                    onClick={handleAddCategory}
                    className="px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600 text-sm"
                  >
                    Add
                  </button>
                  <button
                    type="button"
                    onClick={() => {setShowNewCategory(false); setNewCategory('');}}
                    className="px-3 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({...formData, priority: e.target.value})}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {priorities.map(priority => (
                  <option key={priority} value={priority}>{priority}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
              <input
                type="datetime-local"
                value={formData.due_date}
                onChange={(e) => setFormData({...formData, due_date: e.target.value})}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reminder</label>
              <input
                type="datetime-local"
                value={formData.reminder}
                onChange={(e) => setFormData({...formData, reminder: e.target.value})}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              className="flex-1 bg-blue-500 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-600 transition-colors"
            >
              {task ? 'Update Task' : 'Create Task'}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 bg-gray-500 text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-600 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const TaskItem = ({ task, onToggle, onEdit, onDelete }) => {
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'High': return 'text-red-600 bg-red-50';
      case 'Medium': return 'text-yellow-600 bg-yellow-50';
      case 'Low': return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const isOverdue = task.due_date && new Date(task.due_date) < new Date() && !task.completed;

  return (
    <div className={`p-4 rounded-lg border ${task.completed ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-300'} ${isOverdue ? 'border-red-300 bg-red-50' : ''}`}>
      <div className="flex items-start gap-3">
        <button
          onClick={() => onToggle(task.id, !task.completed)}
          className="mt-1 text-blue-500 hover:text-blue-600"
        >
          {task.completed ? <CheckCircle className="w-5 h-5" /> : <Circle className="w-5 h-5" />}
        </button>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className={`font-medium ${task.completed ? 'line-through text-gray-500' : 'text-gray-900'}`}>
              {task.title}
            </h3>
            <div className="flex gap-1">
              <button
                onClick={() => onEdit(task)}
                className="text-gray-400 hover:text-blue-500 p-1"
                title="Edit task"
              >
                <Edit3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => onDelete(task.id)}
                className="text-gray-400 hover:text-red-500 p-1"
                title="Delete task"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {task.description && (
            <p className={`text-sm mt-1 ${task.completed ? 'text-gray-400' : 'text-gray-600'}`}>
              {task.description}
            </p>
          )}
          
          <div className="flex flex-wrap gap-2 mt-2">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(task.priority)}`}>
              {task.priority}
            </span>
            <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
              {task.category}
            </span>
            {task.due_date && (
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${isOverdue ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-700'}`}>
                Due: {formatDate(task.due_date)}
              </span>
            )}
            {task.reminder && (
              <span className="px-2 py-1 bg-orange-50 text-orange-700 rounded-full text-xs font-medium">
                <Bell className="w-3 h-3 inline mr-1" />
                {formatDate(task.reminder)}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Calendar Components
const CalendarView = ({ events, selectedDate, onDateChange, viewType, onViewTypeChange }) => {
  const [currentMonth, setCurrentMonth] = useState(new Date());

  const monthNames = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];

  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    const days = [];
    
    // Add empty slots for days before month starts
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null);
    }
    
    // Add all days of the month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(new Date(year, month, i));
    }
    
    return days;
  };

  const isToday = (date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const isSelected = (date) => {
    return selectedDate && date.toDateString() === selectedDate.toDateString();
  };

  const getEventsForDate = (date) => {
    return events.filter(event => {
      const eventDate = new Date(event.start_time);
      return eventDate.toDateString() === date.toDateString();
    });
  };

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  };

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  };

  const days = getDaysInMonth(currentMonth);

  if (viewType === 'list') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Upcoming Events</h3>
          <button
            onClick={() => onViewTypeChange('grid')}
            className="p-2 text-gray-500 hover:text-blue-500"
            title="Switch to calendar view"
          >
            <LayoutGrid className="w-5 h-5" />
          </button>
        </div>
        
        <div className="space-y-3">
          {events.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Calendar className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p>No upcoming events</p>
            </div>
          ) : (
            events.map(event => (
              <div key={event.id} className="p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900">{event.title}</h4>
                    {event.description && (
                      <p className="text-sm text-gray-600 mt-1">{event.description}</p>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                      <span>{new Date(event.start_time).toLocaleDateString()}</span>
                      {!event.all_day && (
                        <span>
                          {new Date(event.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} - 
                          {new Date(event.end_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </span>
                      )}
                      {event.location && <span>📍 {event.location}</span>}
                    </div>
                  </div>
                  <div className={`w-3 h-3 rounded-full ${event.all_day ? 'bg-green-500' : 'bg-blue-500'}`}></div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold">
            {monthNames[currentMonth.getMonth()]} {currentMonth.getFullYear()}
          </h3>
          <div className="flex gap-2">
            <button
              onClick={prevMonth}
              className="p-2 text-gray-500 hover:text-blue-500 hover:bg-blue-50 rounded"
            >
              ←
            </button>
            <button
              onClick={nextMonth}
              className="p-2 text-gray-500 hover:text-blue-500 hover:bg-blue-50 rounded"
            >
              →
            </button>
          </div>
        </div>
        <button
          onClick={() => onViewTypeChange('list')}
          className="p-2 text-gray-500 hover:text-blue-500"
          title="Switch to list view"
        >
          <List className="w-5 h-5" />
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200">
        <div className="grid grid-cols-7 gap-0 border-b border-gray-200">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="p-3 text-center text-sm font-medium text-gray-500 border-r border-gray-200 last:border-r-0">
              {day}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-0">
          {days.map((day, index) => (
            <div
              key={index}
              className={`min-h-24 p-2 border-r border-b border-gray-200 last:border-r-0 ${
                !day ? 'bg-gray-50' : 'bg-white hover:bg-blue-50 cursor-pointer'
              }`}
              onClick={() => day && onDateChange(day)}
            >
              {day && (
                <div>
                  <div className={`text-sm font-medium mb-1 ${
                    isToday(day) ? 'bg-blue-500 text-white w-6 h-6 rounded-full flex items-center justify-center' :
                    isSelected(day) ? 'bg-blue-100 text-blue-700 w-6 h-6 rounded-full flex items-center justify-center' :
                    'text-gray-900'
                  }`}>
                    {day.getDate()}
                  </div>
                  <div className="space-y-1">
                    {getEventsForDate(day).slice(0, 2).map((event, eventIndex) => (
                      <div
                        key={eventIndex}
                        className={`text-xs p-1 rounded truncate ${
                          event.all_day ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                        }`}
                        title={event.title}
                      >
                        {event.title}
                      </div>
                    ))}
                    {getEventsForDate(day).length > 2 && (
                      <div className="text-xs text-gray-500">
                        +{getEventsForDate(day).length - 2} more
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Main Dashboard Component
const Dashboard = () => {
  const { user, logout } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [events, setEvents] = useState([]);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [filter, setFilter] = useState({ completed: null, category: null });
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [calendarViewType, setCalendarViewType] = useState('grid');
  const [activeTab, setActiveTab] = useState('dashboard');
  const [summary, setSummary] = useState(null);
  const [availableCategories, setAvailableCategories] = useState([]);

  useEffect(() => {
    fetchTasks();
    fetchEvents();
    fetchSummary();
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/tasks/categories`);
      const userCategories = response.data;
      const defaultCategories = ['General', 'Work', 'Personal', 'Health', 'Shopping', 'Finance'];
      const allCategories = [...new Set([...defaultCategories, ...userCategories])];
      setAvailableCategories(allCategories);
    } catch (error) {
      console.error('Error fetching categories:', error);
      setAvailableCategories(['General', 'Work', 'Personal', 'Health', 'Shopping', 'Finance']);
    }
  };

  const fetchTasks = async () => {
    try {
      const params = new URLSearchParams();
      if (filter.completed !== null) params.append('completed', filter.completed);
      if (filter.category) params.append('category', filter.category);
      
      const response = await axios.get(`${API}/tasks?${params}`);
      setTasks(response.data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  const fetchEvents = async () => {
    try {
      const response = await axios.get(`${API}/calendar/events`);
      setEvents(response.data);
    } catch (error) {
      console.error('Error fetching events:', error);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/summary`);
      setSummary(response.data);
    } catch (error) {
      console.error('Error fetching summary:', error);
    }
  };

  const createTask = async (taskData) => {
    try {
      await axios.post(`${API}/tasks`, taskData);
      fetchTasks();
      fetchSummary();
      fetchCategories();
      setShowTaskForm(false);
    } catch (error) {
      console.error('Error creating task:', error);
    }
  };

  const updateTask = async (taskData) => {
    try {
      await axios.put(`${API}/tasks/${editingTask.id}`, taskData);
      fetchTasks();
      fetchSummary();
      fetchCategories();
      setEditingTask(null);
    } catch (error) {
      console.error('Error updating task:', error);
    }
  };

  const toggleTask = async (taskId, completed) => {
    try {
      await axios.put(`${API}/tasks/${taskId}`, { completed });
      fetchTasks();
      fetchSummary();
    } catch (error) {
      console.error('Error toggling task:', error);
    }
  };

  const deleteTask = async (taskId) => {
    if (window.confirm('Are you sure you want to delete this task?')) {
      try {
        await axios.delete(`${API}/tasks/${taskId}`);
        fetchTasks();
        fetchSummary();
      } catch (error) {
        console.error('Error deleting task:', error);
      }
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [filter]);

  const renderDashboard = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Welcome back, {user.name}!</h2>
          <p className="text-gray-600">Here's your overview for today</p>
        </div>
        <img
          src={user.picture}
          alt={user.name}
          className="w-12 h-12 rounded-full border-2 border-blue-200"
        />
      </div>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-6 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100">Total Tasks</p>
                <p className="text-3xl font-bold">{summary.task_stats.total}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-blue-200" />
            </div>
          </div>

          <div className="bg-gradient-to-r from-green-500 to-green-600 text-white p-6 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-100">Completed</p>
                <p className="text-3xl font-bold">{summary.task_stats.completed}</p>
              </div>
              <Circle className="w-8 h-8 text-green-200" />
            </div>
          </div>

          <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-6 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-orange-100">Today's Tasks</p>
                <p className="text-3xl font-bold">{summary.today_tasks_count}</p>
              </div>
              <Calendar className="w-8 h-8 text-orange-200" />
            </div>
          </div>

          <div className="bg-gradient-to-r from-purple-500 to-purple-600 text-white p-6 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-purple-100">Upcoming Events</p>
                <p className="text-3xl font-bold">{summary.upcoming_events_count}</p>
              </div>
              <Bell className="w-8 h-8 text-purple-200" />
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Tasks</h3>
          <div className="space-y-3">
            {tasks.slice(0, 5).map(task => (
              <TaskItem
                key={task.id}
                task={task}
                onToggle={toggleTask}
                onEdit={setEditingTask}
                onDelete={deleteTask}
              />
            ))}
            {tasks.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p>No tasks yet. Create your first task!</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold mb-4">Upcoming Events</h3>
          <div className="space-y-3">
            {events.slice(0, 3).map(event => (
              <div key={event.id} className="p-3 border border-gray-200 rounded-lg">
                <h4 className="font-medium text-gray-900">{event.title}</h4>
                <p className="text-sm text-gray-600 mt-1">
                  {new Date(event.start_time).toLocaleDateString()} at{' '}
                  {new Date(event.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                </p>
                {event.location && (
                  <p className="text-sm text-gray-500">📍 {event.location}</p>
                )}
              </div>
            ))}
            {events.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                <Calendar className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p>No upcoming events</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  const renderTasks = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Task Management</h2>
        <button
          onClick={() => setShowTaskForm(true)}
          className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          New Task
        </button>
      </div>

      <div className="flex flex-wrap gap-4 items-center">
        <select
          value={filter.completed || ''}
          onChange={(e) => setFilter({...filter, completed: e.target.value === '' ? null : e.target.value === 'true'})}
          className="p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">All Tasks</option>
          <option value="false">Pending</option>
          <option value="true">Completed</option>
        </select>

        <select
          value={filter.category || ''}
          onChange={(e) => setFilter({...filter, category: e.target.value || null})}
          className="p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">All Categories</option>
          <option value="General">General</option>
          <option value="Work">Work</option>
          <option value="Personal">Personal</option>
          <option value="Health">Health</option>
          <option value="Shopping">Shopping</option>
          <option value="Finance">Finance</option>
        </select>
      </div>

      <div className="space-y-4">
        {tasks.map(task => (
          <TaskItem
            key={task.id}
            task={task}
            onToggle={toggleTask}
            onEdit={setEditingTask}
            onDelete={deleteTask}
          />
        ))}
        {tasks.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No tasks found matching your filters</p>
          </div>
        )}
      </div>
    </div>
  );

  const renderCalendar = () => (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Calendar</h2>
      <CalendarView
        events={events}
        selectedDate={selectedDate}
        onDateChange={setSelectedDate}
        viewType={calendarViewType}
        onViewTypeChange={setCalendarViewType}
      />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <Calendar className="w-8 h-8 text-blue-500" />
              <span className="text-xl font-bold text-gray-900">Calendar & Tasks</span>
            </div>
            
            <div className="flex gap-1">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'dashboard' ? 'bg-blue-500 text-white' : 'text-gray-600 hover:text-blue-500 hover:bg-blue-50'
                }`}
              >
                Dashboard
              </button>
              <button
                onClick={() => setActiveTab('tasks')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'tasks' ? 'bg-blue-500 text-white' : 'text-gray-600 hover:text-blue-500 hover:bg-blue-50'
                }`}
              >
                Tasks
              </button>
              <button
                onClick={() => setActiveTab('calendar')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'calendar' ? 'bg-blue-500 text-white' : 'text-gray-600 hover:text-blue-500 hover:bg-blue-50'
                }`}
              >
                Calendar
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-gray-600">Hello, {user.name}</span>
            <button
              onClick={logout}
              className="text-gray-500 hover:text-red-500 p-2"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto p-6">
        {activeTab === 'dashboard' && renderDashboard()}
        {activeTab === 'tasks' && renderTasks()}
        {activeTab === 'calendar' && renderCalendar()}
      </main>

      {showTaskForm && (
        <TaskForm
          onSubmit={createTask}
          onCancel={() => setShowTaskForm(false)}
        />
      )}

      {editingTask && (
        <TaskForm
          task={editingTask}
          onSubmit={updateTask}
          onCancel={() => setEditingTask(null)}
        />
      )}
    </div>
  );
};

// Main App Component
const App = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-blue-500 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse">
            <Calendar className="w-8 h-8 text-white" />
          </div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return user ? <Dashboard /> : <LoginPage />;
};

const AppWithAuth = () => (
  <AuthProvider>
    <App />
  </AuthProvider>
);

export default AppWithAuth;