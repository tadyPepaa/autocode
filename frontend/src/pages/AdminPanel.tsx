import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useUsers, useCreateUser, useDeleteUser } from '../api/users';

export default function AdminPanel() {
  const { user: currentUser } = useAuth();
  const { data: users, isLoading } = useUsers();
  const createUser = useCreateUser();
  const deleteUser = useDeleteUser();

  const [showModal, setShowModal] = useState(false);
  const [newUser, setNewUser] = useState({
    username: '',
    password: '',
    role: 'user',
  });
  const [createError, setCreateError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  // Admin-only access check
  if (currentUser?.role !== 'admin') {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-red-700 bg-red-900/30 p-6 text-center">
          <h2 className="mb-2 text-lg font-bold text-red-300">Access Denied</h2>
          <p className="text-gray-400">
            You do not have permission to access the admin panel. Only
            administrators can manage users.
          </p>
        </div>
      </div>
    );
  }

  async function handleCreateUser(e: React.FormEvent) {
    e.preventDefault();
    setCreateError('');
    if (!newUser.username.trim()) {
      setCreateError('Username is required.');
      return;
    }
    if (!newUser.password.trim()) {
      setCreateError('Password is required.');
      return;
    }
    try {
      await createUser.mutateAsync({
        username: newUser.username.trim(),
        password: newUser.password,
        role: newUser.role,
      });
      setShowModal(false);
      setNewUser({ username: '', password: '', role: 'user' });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      if (axiosErr.response?.data?.detail) {
        setCreateError(axiosErr.response.data.detail);
      } else {
        setCreateError('Failed to create user.');
      }
    }
  }

  function handleDelete(userId: number) {
    deleteUser.mutate(userId, {
      onSuccess: () => setDeleteConfirm(null),
    });
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Admin Panel</h1>
          <p className="mt-1 text-sm text-gray-400">Manage users and roles</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-blue-500"
        >
          + New User
        </button>
      </div>

      {/* Users Table */}
      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-12 animate-pulse rounded-lg bg-gray-800"
            />
          ))}
        </div>
      )}

      {!isLoading && users && users.length === 0 && (
        <p className="text-gray-500">No users found.</p>
      )}

      {!isLoading && users && users.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-700">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-800 text-gray-400">
              <tr>
                <th className="px-4 py-3 font-medium">Username</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3 font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-white">{u.username}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium text-white ${
                        u.role === 'admin' ? 'bg-purple-600' : 'bg-gray-600'
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.role === 'admin' ? (
                      <span className="text-xs text-gray-500">Protected</span>
                    ) : deleteConfirm === u.id ? (
                      <div className="inline-flex items-center gap-2">
                        <span className="text-xs text-red-300">Confirm?</span>
                        <button
                          onClick={() => handleDelete(u.id)}
                          disabled={deleteUser.isPending}
                          className="rounded bg-red-700 px-3 py-1 text-xs text-white transition hover:bg-red-600 disabled:opacity-50"
                        >
                          {deleteUser.isPending ? 'Deleting...' : 'Yes'}
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(null)}
                          className="rounded bg-gray-700 px-3 py-1 text-xs text-white transition hover:bg-gray-600"
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setDeleteConfirm(u.id)}
                        className="rounded bg-red-700 px-3 py-1 text-xs text-white transition hover:bg-red-600"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create User Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-xl bg-gray-800 p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-bold text-white">New User</h3>

            {createError && (
              <div className="mb-3 rounded-lg bg-red-900/50 px-3 py-2 text-sm text-red-300">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Username <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) =>
                    setNewUser((u) => ({ ...u, username: e.target.value }))
                  }
                  placeholder="Username"
                  className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Password <span className="text-red-400">*</span>
                </label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) =>
                    setNewUser((u) => ({ ...u, password: e.target.value }))
                  }
                  placeholder="Password"
                  className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Role
                </label>
                <select
                  value={newUser.role}
                  onChange={(e) =>
                    setNewUser((u) => ({ ...u, role: e.target.value }))
                  }
                  className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setCreateError('');
                  }}
                  className="rounded-lg border border-gray-600 px-4 py-2 text-sm text-gray-300 transition hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createUser.isPending}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {createUser.isPending ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
