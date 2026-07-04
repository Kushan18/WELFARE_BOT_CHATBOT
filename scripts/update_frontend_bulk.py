import re
import os

filepath = r"c:\Users\kusha\OneDrive\Desktop\Welfare_Bot_Final\frontend\src\components\AdminDashboard.js"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add state
state_code = """
  const [expandedFeedbackId, setExpandedFeedbackId] = useState(null);
  const [selectedSchemes, setSelectedSchemes] = useState([]);
"""
content = content.replace("  const [expandedFeedbackId, setExpandedFeedbackId] = useState(null);", state_code.strip('\n'))

# 2. Add handlers
handlers_code = """
  const handleSelectScheme = (schemeId) => {
    setSelectedSchemes(prev => prev.includes(schemeId) ? prev.filter(id => id !== schemeId) : [...prev, schemeId]);
  };

  const handleSelectAll = (schemesList) => {
    if (selectedSchemes.length === schemesList.length) {
      setSelectedSchemes([]);
    } else {
      setSelectedSchemes(schemesList.map(s => s._id));
    }
  };

  const handleBulkDelete = async (sourceType, currentSchemesList) => {
    if (selectedSchemes.length === 0) return;
    if (!window.confirm(`Delete ${selectedSchemes.length} selected schemes?`)) return;
    try {
      const items = selectedSchemes.map(id => {
        const scheme = currentSchemesList.find(s => s._id === id);
        return { id, source: scheme ? scheme.source : 'official' };
      });
      await axios.post(API + '/admin/schemes/bulk_delete', items, { headers });
      addToast(`Deleted ${selectedSchemes.length} schemes`);
      setSelectedSchemes([]);
      handleRefresh();
    } catch (e) {
      addToast('Bulk delete failed.');
    }
  };

  const handleBulkHardDelete = async () => {
    if (selectedSchemes.length === 0) return;
    if (!window.confirm(`Permanently delete ${selectedSchemes.length} schemes?`)) return;
    try {
      await axios.post(API + '/admin/deleted/bulk_hard_delete', selectedSchemes, { headers });
      addToast(`Permanently deleted ${selectedSchemes.length} schemes`);
      setSelectedSchemes([]);
      handleRefresh();
    } catch (e) {
      addToast('Bulk delete failed.');
    }
  };
"""
content = content.replace("  const handleDeleteScrapeRun = async (run) => {", handlers_code.lstrip('\n') + "\n  const handleDeleteScrapeRun = async (run) => {")

# Clear selection when tabs change
content = content.replace("setActiveTab(key);", "setActiveTab(key);\n    setSelectedSchemes([]);")

# 3. Add to Schemes Table
schemes_th = """
                    <tr>
                      <th>
                        <input type="checkbox" checked={schemesData && schemesData.length > 0 && selectedSchemes.length === schemesData.length} onChange={() => handleSelectAll(schemesData)} />
                      </th>
                      <th>Name</th><th>State</th><th>Verified</th><th>Source</th><th>Actions</th>
                    </tr>
"""
content = re.sub(r"<tr><th>Name</th><th>State</th><th>Verified</th><th>Source</th><th>Actions</th></tr>", schemes_th.strip('\n'), content, count=1)

schemes_td = """
                        <td>
                          <input type="checkbox" checked={selectedSchemes.includes(s._id)} onChange={() => handleSelectScheme(s._id)} />
                        </td>
                        <td>
"""
content = re.sub(r"(<tr key=\{s\._id \|\| i\}.*?>\s*)<td>", r"\1" + schemes_td.strip('\n'), content, count=1)

schemes_bulk_btn = """
              <div className='table-container'>
                {selectedSchemes.length > 0 && (
                  <div style={{marginBottom: '10px'}}>
                    <button className='btn-table-action btn-delete' onClick={() => handleBulkDelete('official', schemesData)}>Delete Selected ({selectedSchemes.length})</button>
                  </div>
                )}
                <table className='admin-table'>
"""
content = content.replace("<div className='table-container'>\n                <table className='admin-table'>", schemes_bulk_btn.lstrip('\n'), 1)

# 4. Add to New Schemes Table
new_schemes_th = """
                    <tr>
                      <th>
                        <input type="checkbox" checked={newSchemesData && newSchemesData.length > 0 && selectedSchemes.length === newSchemesData.length} onChange={() => handleSelectAll(newSchemesData)} />
                      </th>
                      <th>Name</th><th>State</th><th>Verified</th><th>Source</th><th>Actions</th>
                    </tr>
"""
content = re.sub(r"<tr><th>Name</th><th>State</th><th>Verified</th><th>Source</th><th>Actions</th></tr>", new_schemes_th.strip('\n'), content, count=1) # count 1 because we did first one

new_schemes_td = """
                        <td>
                          <input type="checkbox" checked={selectedSchemes.includes(s._id)} onChange={() => handleSelectScheme(s._id)} />
                        </td>
                        <td>
"""
content = re.sub(r"(<tr key=\{s\._id \|\| i\}.*?>\s*)<td>", r"\1" + new_schemes_td.strip('\n'), content, count=1) # 2nd occurrence

new_schemes_bulk_btn = """
              <div className='table-container'>
                {selectedSchemes.length > 0 && (
                  <div style={{marginBottom: '10px'}}>
                    <button className='btn-table-action btn-delete' onClick={() => handleBulkDelete('new', newSchemesData)}>Delete Selected ({selectedSchemes.length})</button>
                  </div>
                )}
                <table className='admin-table'>
"""
content = content.replace("<div className='table-container'>\n                <table className='admin-table'>", new_schemes_bulk_btn.lstrip('\n'), 1)

# 5. Add to Deleted Schemes Table
deleted_schemes_th = """
                    <tr>
                      <th>
                        <input type="checkbox" checked={deletedSchemes && deletedSchemes.length > 0 && selectedSchemes.length === deletedSchemes.length} onChange={() => handleSelectAll(deletedSchemes)} />
                      </th>
                      <th>Name</th><th>State</th><th>Source</th><th>Actions</th>
                    </tr>
"""
content = re.sub(r"<tr><th>Name</th><th>State</th><th>Source</th><th>Actions</th></tr>", deleted_schemes_th.strip('\n'), content, count=1)

deleted_schemes_td = """
                        <tr key={s._id || i} className="animate-row" style={{animationDelay: getAnimationDelay(i)}}>
                          <td>
                            <input type="checkbox" checked={selectedSchemes.includes(s._id)} onChange={() => handleSelectScheme(s._id)} />
                          </td>
                          <td>{s.name || 'Unnamed'}</td>
"""
content = re.sub(r'<tr key=\{s\._id \|\| i\} className="animate-row" style=\{\{animationDelay: getAnimationDelay\(i\)\}\}>\s*<td>\{s\.name \|\| \'Unnamed\'\}</td>', deleted_schemes_td.strip('\n'), content, count=1)

deleted_schemes_bulk_btn = """
              <div className='table-container'>
                {selectedSchemes.length > 0 && (
                  <div style={{marginBottom: '10px'}}>
                    <button className='btn-table-action btn-hard-delete' onClick={() => handleBulkHardDelete()}>Permanently Delete Selected ({selectedSchemes.length})</button>
                  </div>
                )}
                <table className='admin-table'>
"""
content = content.replace("<div className='table-container'>\n                <table className='admin-table'>", deleted_schemes_bulk_btn.lstrip('\n'), 1)


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated AdminDashboard.js")
