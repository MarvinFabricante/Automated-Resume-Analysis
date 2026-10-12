/**
 * Utility to export an array of objects to a CSV file.
 * @param {Array<Record<string, any>>} data - The array of objects to export.
 * @param {string} fileName - The name of the file (without extension).
 */
export const exportToCSV = (data: Record<string, any>[], fileName: string): void => {
  if (!data || !data.length) {
    alert("No data available to export.");
    return;
  }

  // Get headers from the first object
  const headers = Object.keys(data[0]);
  
  // Create CSV rows
  const csvRows = [
    headers.join(','), // Header row
    ...data.map(row => 
      headers.map(header => {
        const val = row[header] === null || row[header] === undefined ? "" : row[header];
        // Escape quotes and wrap in quotes if contains comma
        const escaped = ('' + val).replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(',')
    )
  ];

  const csvString = csvRows.join('\n');
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `${fileName}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
