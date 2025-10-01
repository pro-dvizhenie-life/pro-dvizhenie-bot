import React from 'react'
import cls from './Dashboard.module.css'
import { ApplicationsTable } from 'src/components/ApplicationsTable/ApplicationsTable'
import { applicationsData } from 'src/shared/const/testApplicationsData'

// interface Props {
// }

const Dashboard: React.FC = () => {
	return <div className={cls.Dashboard}>DASHBOARD 
    <ApplicationsTable applications={applicationsData} />
    </div>
}

export default Dashboard
