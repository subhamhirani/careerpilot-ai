'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useSettingsStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { Save, Plus, Trash2, Settings, Search, Bell, Shield } from 'lucide-react';
import type { UserSettings, SearchQuery } from '@/types';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { settings, setSettings, loading, setLoading } = useSettingsStore();

  // Local form state
  const [notificationEnabled, setNotificationEnabled] = useState(true);
  const [autoApply, setAutoApply] = useState(false);
  const [maxPerDay, setMaxPerDay] = useState(5);
  const [searchQueries, setSearchQueries] = useState<SearchQuery[]>([]);

  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get<UserSettings>('/settings'),
  });

  useEffect(() => {
    if (data) {
      setSettings(data);
      setNotificationEnabled(data.notification_enabled);
      setAutoApply(data.auto_apply);
      setMaxPerDay(data.max_applications_per_day);
      setSearchQueries(data.search_queries || []);
    }
    setLoading(isLoading);
  }, [data, isLoading, setSettings, setLoading]);

  const saveMutation = useMutation({
    mutationFn: (body: Partial<UserSettings>) =>
      api.put<UserSettings>('/settings', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      toast.success('Settings saved successfully');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to save settings');
    },
  });

  const handleSaveGeneral = () => {
    saveMutation.mutate({
      notification_enabled: notificationEnabled,
      auto_apply: autoApply,
      max_applications_per_day: maxPerDay,
    });
  };

  const handleSaveSearch = () => {
    saveMutation.mutate({
      search_queries: searchQueries,
    });
  };

  const addSearchQuery = () => {
    setSearchQueries([
      ...searchQueries,
      {
        id: `new-${Date.now()}`,
        query: '',
        location: '',
        tiers: [],
        sources: [],
        active: true,
      },
    ]);
  };

  const updateSearchQuery = (id: string, field: keyof SearchQuery, value: any) => {
    setSearchQueries(
      searchQueries.map((q) => (q.id === id ? { ...q, [field]: value } : q))
    );
  };

  const removeSearchQuery = (id: string) => {
    setSearchQueries(searchQueries.filter((q) => q.id !== id));
  };

  if (loading && !settings) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-96 rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Configure your CareerPilot preferences
        </p>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="search" className="flex items-center gap-2">
            <Search className="h-4 w-4" />
            Search Queries
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Notifications
          </TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Application Preferences</CardTitle>
              <CardDescription>
                Configure how CareerPilot handles job applications
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="auto-apply">Auto-Apply</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically apply to matching jobs without manual approval
                  </p>
                </div>
                <Switch
                  id="auto-apply"
                  checked={autoApply}
                  onCheckedChange={setAutoApply}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="max-daily">Max Applications Per Day</Label>
                  <p className="text-sm text-muted-foreground">
                    Limit the number of automated applications per day
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    id="max-daily"
                    type="number"
                    className="w-20 text-center"
                    min={1}
                    max={50}
                    value={maxPerDay}
                    onChange={(e) => setMaxPerDay(parseInt(e.target.value) || 1)}
                  />
                </div>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="notifications">Email Notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Receive email notifications for approvals and updates
                  </p>
                </div>
                <Switch
                  id="notifications"
                  checked={notificationEnabled}
                  onCheckedChange={setNotificationEnabled}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveGeneral} disabled={saveMutation.isPending}>
              <Save className="h-4 w-4 mr-2" />
              {saveMutation.isPending ? 'Saving...' : 'Save Settings'}
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="search" className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Search Queries</CardTitle>
                <CardDescription>
                  Manage the search queries CareerPilot uses to find jobs
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={addSearchQuery}>
                <Plus className="h-4 w-4 mr-1" />
                Add Query
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {searchQueries.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No search queries configured</p>
                  <p className="text-xs">Add a search query to start finding jobs</p>
                </div>
              ) : (
                searchQueries.map((query, index) => (
                  <div key={query.id} className="p-4 border rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Query {index + 1}</span>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={query.active}
                          onCheckedChange={(v) => updateSearchQuery(query.id, 'active', v)}
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-700"
                          onClick={() => removeSearchQuery(query.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Keywords</Label>
                        <Input
                          placeholder="e.g. software engineer"
                          value={query.query}
                          onChange={(e) => updateSearchQuery(query.id, 'query', e.target.value)}
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Location</Label>
                        <Input
                          placeholder="e.g. Remote, New York"
                          value={query.location || ''}
                          onChange={(e) => updateSearchQuery(query.id, 'location', e.target.value)}
                        />
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(['tier_a', 'tier_b', 'tier_c'] as const).map((tier) => (
                        <Badge
                          key={tier}
                          variant={query.tiers?.includes(tier) ? 'default' : 'outline'}
                          className="cursor-pointer"
                          onClick={() => {
                            const current = query.tiers || [];
                            const updated = current.includes(tier)
                              ? current.filter((t) => t !== tier)
                              : [...current, tier];
                            updateSearchQuery(query.id, 'tiers', updated);
                          }}
                        >
                          {tier.replace('_', ' ').toUpperCase()}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveSearch} disabled={saveMutation.isPending}>
              <Save className="h-4 w-4 mr-2" />
              {saveMutation.isPending ? 'Saving...' : 'Save Search Queries'}
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Configure how you receive updates about your job search
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Application Approvals</Label>
                  <p className="text-sm text-muted-foreground">
                    When new applications need your approval
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Application Submitted</Label>
                  <p className="text-sm text-muted-foreground">
                    When an application is successfully submitted
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Interview Invitations</Label>
                  <p className="text-sm text-muted-foreground">
                    When you receive an interview invitation
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Weekly Digest</Label>
                  <p className="text-sm text-muted-foreground">
                    Weekly summary of your job search activity
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
