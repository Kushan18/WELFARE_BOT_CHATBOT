import re
import os

filepath = r"c:\Users\kusha\OneDrive\Desktop\Welfare_Bot_Final\frontend\src\components\AdminDashboard.js"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add isSelectionMode state
if "const [isSelectionMode, setIsSelectionMode] = useState(false);" not in content:
    content = content.replace(
        "const [selectedSchemes, setSelectedSchemes] = useState([]);",
        "const [selectedSchemes, setSelectedSchemes] = useState([]);\n  const [isSelectionMode, setIsSelectionMode] = useState(false);"
    )

# 2. Reset mode on tab change
content = content.replace(
    "setActiveTab(key);\n    setSelectedSchemes([]);",
    "setActiveTab(key);\n    setSelectedSchemes([]);\n    setIsSelectionMode(false);"
)

# 3. Update Schemes Table Top Buttons
old_schemes_bulk = """              <div className='table-container'>
                {selectedSchemes.length > 0 && (
                  <div style={{marginBottom: '10px'}}>
                    <button className='btn-table-action btn-delete' onClick={() => handleBulkDelete('official', schemesData)}>Delete Selected ({selectedSchemes.length})</button>
                  </div>
                )}
                <table className='admin-table'>"""
new_schemes_bulk = """              <div className='table-container'>
                <div style={{marginBottom: '10px', display: 'flex', gap: '10px'}}>
                  <button className='btn-table-action' style={{background: isSelectionMode ? 'var(--bg-glass)' : 'var(--primary)'}} onClick={() => { setIsSelectionMode(!isSelectionMode); setSelectedSchemes([]); }}>
                    {isSelectionMode ? 'Cancel Selection' : 'Select Multiple'}
                  </button>
                  {isSelectionMode && selectedSchemes.length > 0 && (
                    <button className='btn-table-action btn-delete' onClick={() => handleBulkDelete('official', schemesData)}>Delete Selected ({selectedSchemes.length})</button>
                  )}
                </div>
                <table className='admin-table'>"""
content = content.replace(old_schemes_bulk, new_schemes_bulk)

# 4. Update New Schemes Table Top Buttons
old_new_bulk = """              <div className='table-container'>
                {selectedSchemes.length > 0 && (
                  <div style={{marginBottom: '10px'}}>
                    <button className='btn-table-action btn-delete' onClick={() => handleBulkDelete('new', newSchemesData)}>Delete Selected ({selectedSchemes.length})</button>
                  </div>
                )}
                <table className='admin-table'>"""
new_new_bulk = """              <div className='table-container'>
                <div style={{marginBottom: '10px', display: 'flex', gap: '10px'}}>
                  <button className='btn-table-action' style={{background: isSelectionMode ? 'var(--bg-glass)' : 'var(--primary)'}} onClick={() => { setIsSelectionMode(!isSelectionMode); setSelectedSchemes([]); }}>
                    {isSelectionMode ? 'Cancel Selection' : 'Select Multiple'}
                  </button>
                  {isSelectionMode && selectedSchemes.length > 0 && (
                    <button className='btn-table-action btn-delete' onClick={() => handleBulkDelete('new', newSchemesData)}>Delete Selected ({selectedSchemes.length})</button>
                  )}
                </div>
                <table className='admin-table'>"""
content = content.replace(old_new_bulk, new_new_bulk)

# 5. Update Deleted Schemes Table Top Buttons
old_del_bulk = """              <div className='table-container'>
                {selectedSchemes.length > 0 && (
                  <div style={{marginBottom: '10px'}}>
                    <button className='btn-table-action btn-hard-delete' onClick={() => handleBulkHardDelete()}>Permanently Delete Selected ({selectedSchemes.length})</button>
                  </div>
                )}
                <table className='admin-table'>"""
new_del_bulk = """              <div className='table-container'>
                <div style={{marginBottom: '10px', display: 'flex', gap: '10px'}}>
                  <button className='btn-table-action' style={{background: isSelectionMode ? 'var(--bg-glass)' : 'var(--primary)'}} onClick={() => { setIsSelectionMode(!isSelectionMode); setSelectedSchemes([]); }}>
                    {isSelectionMode ? 'Cancel Selection' : 'Select Multiple'}
                  </button>
                  {isSelectionMode && selectedSchemes.length > 0 && (
                    <button className='btn-table-action btn-hard-delete' onClick={() => handleBulkHardDelete()}>Permanently Delete Selected ({selectedSchemes.length})</button>
                  )}
                </div>
                <table className='admin-table'>"""
content = content.replace(old_del_bulk, new_del_bulk)

# 6. Conditionally render the TH tags
content = content.replace("""                      <th>
                        <input type="checkbox" checked={schemesData && schemesData.length > 0 && selectedSchemes.length === schemesData.length} onChange={() => handleSelectAll(schemesData)} />
                      </th>""", """                      {isSelectionMode && (
                        <th>
                          <input type="checkbox" checked={schemesData && schemesData.length > 0 && selectedSchemes.length === schemesData.length} onChange={() => handleSelectAll(schemesData)} />
                        </th>
                      )}""")

content = content.replace("""                      <th>
                        <input type="checkbox" checked={newSchemesData && newSchemesData.length > 0 && selectedSchemes.length === newSchemesData.length} onChange={() => handleSelectAll(newSchemesData)} />
                      </th>""", """                      {isSelectionMode && (
                        <th>
                          <input type="checkbox" checked={newSchemesData && newSchemesData.length > 0 && selectedSchemes.length === newSchemesData.length} onChange={() => handleSelectAll(newSchemesData)} />
                        </th>
                      )}""")

content = content.replace("""                      <th>
                        <input type="checkbox" checked={deletedSchemes && deletedSchemes.length > 0 && selectedSchemes.length === deletedSchemes.length} onChange={() => handleSelectAll(deletedSchemes)} />
                      </th>""", """                      {isSelectionMode && (
                        <th>
                          <input type="checkbox" checked={deletedSchemes && deletedSchemes.length > 0 && selectedSchemes.length === deletedSchemes.length} onChange={() => handleSelectAll(deletedSchemes)} />
                        </th>
                      )}""")

# 7. Conditionally render the TD tags
content = content.replace("""                        <td>
                          <input type="checkbox" checked={selectedSchemes.includes(s._id)} onChange={() => handleSelectScheme(s._id)} />
                        </td>""", """                        {isSelectionMode && (
                          <td>
                            <input type="checkbox" checked={selectedSchemes.includes(s._id)} onChange={() => handleSelectScheme(s._id)} />
                          </td>
                        )}""")

content = content.replace("""                          <td>
                            <input type="checkbox" checked={selectedSchemes.includes(s._id)} onChange={() => handleSelectScheme(s._id)} />
                          </td>""", """                          {isSelectionMode && (
                            <td>
                              <input type="checkbox" checked={selectedSchemes.includes(s._id)} onChange={() => handleSelectScheme(s._id)} />
                            </td>
                          )}""")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Selection mode script executed successfully")
