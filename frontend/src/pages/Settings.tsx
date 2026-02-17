import { useState } from 'react';
import { useApiKeys, useAddApiKey, useDeleteApiKey } from '../api/settings';
import { useSocialAccounts, useDisconnectAccount } from '../api/social';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'google', label: 'Google' },
  { value: 'mistral', label: 'Mistral' },
  { value: 'other', label: 'Other' },
];

export default function Settings() {
  const { data: apiKeys, isLoading: keysLoading } = useApiKeys();
  const addKey = useAddApiKey();
  const deleteKey = useDeleteApiKey();

  const { data: accounts, isLoading: accountsLoading } = useSocialAccounts();
  const disconnectAccount = useDisconnectAccount();

  const [provider, setProvider] = useState('openai');
  const [key, setKey] = useState('');
  const [error, setError] = useState('');

  const handleAddKey = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!key.trim()) {
      setError('API key cannot be empty');
      return;
    }
    addKey.mutate(
      { provider, key: key.trim() },
      {
        onSuccess: () => {
          setKey('');
          setError('');
        },
        onError: (err: unknown) => {
          const msg = (err as { response?: { data?: { detail?: string } } })
            ?.response?.data?.detail;
          setError(msg || 'Failed to save API key');
        },
      }
    );
  };

  const handleDeleteKey = (id: number) => {
    deleteKey.mutate(id);
  };

  const handleDisconnect = (id: number) => {
    disconnectAccount.mutate(id);
  };

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-white">Settings</h1>

      {/* API Keys Section */}
      <section className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-white">API Keys</h2>

        {/* Add/Update Form */}
        <form
          onSubmit={handleAddKey}
          className="mb-4 flex flex-col gap-3 rounded-lg border border-gray-700 bg-gray-800 p-4 sm:flex-row sm:items-end"
        >
          <div className="flex-shrink-0">
            <label className="mb-1 block text-sm text-gray-400">Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="rounded-md border border-gray-600 bg-gray-700 px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="mb-1 block text-sm text-gray-400">API Key</label>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="sk-..."
              className="w-full rounded-md border border-gray-600 bg-gray-700 px-3 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={addKey.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {addKey.isPending ? 'Saving...' : 'Save'}
          </button>
        </form>

        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

        {/* Keys Table */}
        {keysLoading ? (
          <div className="h-24 animate-pulse rounded-lg bg-gray-800" />
        ) : apiKeys && apiKeys.length > 0 ? (
          <div className="overflow-hidden rounded-lg border border-gray-700">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-800 text-gray-400">
                <tr>
                  <th className="px-4 py-3">Provider</th>
                  <th className="px-4 py-3">Key</th>
                  <th className="px-4 py-3">Added</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {apiKeys.map((k) => (
                  <tr key={k.id} className="bg-gray-900">
                    <td className="px-4 py-3 font-medium text-white capitalize">
                      {PROVIDERS.find((p) => p.value === k.provider)?.label || k.provider}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-400">
                      {k.masked_key}
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDeleteKey(k.id)}
                        disabled={deleteKey.isPending}
                        className="text-red-400 transition hover:text-red-300 disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="rounded-lg bg-gray-800 p-4 text-center text-gray-400">
            No API keys configured. Add one above to get started.
          </p>
        )}
      </section>

      {/* Connected Accounts Section */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-white">
          Connected Accounts
        </h2>

        {accountsLoading ? (
          <div className="h-24 animate-pulse rounded-lg bg-gray-800" />
        ) : accounts && accounts.length > 0 ? (
          <div className="space-y-3">
            {accounts.map((account) => (
              <div
                key={account.id}
                className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <span className="inline-block rounded-full bg-gray-700 px-3 py-1 text-xs font-medium capitalize text-white">
                    {account.platform}
                  </span>
                  <span className="text-white">{account.account_name}</span>
                  <span className="text-sm text-gray-400">
                    Connected {new Date(account.created_at).toLocaleDateString()}
                  </span>
                </div>
                <button
                  onClick={() => handleDisconnect(account.id)}
                  disabled={disconnectAccount.isPending}
                  className="rounded-md border border-red-600 px-3 py-1 text-sm text-red-400 transition hover:bg-red-600 hover:text-white disabled:opacity-50"
                >
                  Disconnect
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="rounded-lg bg-gray-800 p-4 text-center text-gray-400">
            No connected accounts. Connect social accounts from the Social Media
            page.
          </p>
        )}
      </section>
    </div>
  );
}
